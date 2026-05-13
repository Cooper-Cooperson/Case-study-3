terraform {
  required_version = ">= 1.6.0"

  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 5.35.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region = var.region
  zone = var.zone
  impersonate_service_account = var.service_account
}

# VPC
resource "google_compute_network" "vpc" {
  name = "hub-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet_gke" {
  name          = "subnet-gke"
  ip_cidr_range = "10.50.0.0/20"
  region        = var.region
  network       = google_compute_network.vpc.self_link

  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.51.0.0/20"
  }

  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.52.0.0/24"
  }
}

resource "google_compute_subnetwork" "subnet_db" {
  name = "subnet-db"
  ip_cidr_range = "10.20.0.0/20"
  region = var.region
  network = google_compute_network.vpc.self_link
  #network = google_compute_network.vpc.id
  #private_network = google_compute_network.vpc.self_link
}

resource "google_compute_global_address" "private_ip_range" {
  name          = "sql-private-ip-range"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 20
  network       = google_compute_network.vpc.self_link
}

resource "google_service_networking_connection" "private_vpc_connection" {
  network = google_compute_network.vpc.self_link
  service = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_range.name]
  deletion_policy = "ABANDON" 
}

# Firewall regels
resource "google_compute_firewall" "allow_gke_to_sql" {
  name = "allow-gke-to-sql"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority = 1000

  allow {
    protocol = "tcp"
    ports = ["5432"]
  }

  source_ranges = ["0.0.0.0/0"]   # GKE subnet var 10.50.0.0/20
  target_tags = ["cloud-sql"]
}

resource "google_compute_firewall" "allow_any" {
  name = "allow-any"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority = 1000

  allow {
    protocol = "tcp"
    ports = ["all"]
  }

  source_ranges = ["0.0.0.0/0"]   # GKE subnet var 10.50.0.0/20
  target_tags = ["cloud-sql"]
}
/*
resource "google_compute_firewall" "deny_all_to_sql" {
  name = "deny-all-to-sql"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority = 2000

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/32"]
  target_tags = ["cloud-sql"]
}
*/
resource "google_compute_firewall" "gke_ssh" {
  name = "gke-ssh"
  network = google_compute_network.vpc.name

  direction = "INGRESS"
  priority = 1000

  allow {
    protocol = "tcp"
    ports = ["22"]
  }

  source_ranges = [var.school_ip]
  target_tags = ["gke-node"]
}



resource "google_sql_database_instance" "db" {
  name = "app-db"
  database_version = "POSTGRES_15"
  region = var.region

  settings {
    tier = "db-custom-2-7680"

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.vpc.self_link
    }
  }

  deletion_protection = false
}

resource "google_sql_database" "app" {
  name  = var.db_name
  instance = google_sql_database_instance.db.name
}

resource "google_sql_user" "app" {
  name  = var.db_user
  instance = google_sql_database_instance.db.name
  password = var.db_password
}

#DNS voor DB 
resource "google_dns_managed_zone" "db_internal" {
  name = "db-internal-zone"
  dns_name = "db.internal."
  description = "Private zone for app DB"

  visibility = "private"

  private_visibility_config {
    networks {
      network_url = google_compute_network.vpc.self_link
    }
  }
}

resource "google_dns_record_set" "db_a" {
  name = "app-db.db.internal."
  type = "A"
  ttl = 300
  managed_zone = google_dns_managed_zone.db_internal.name

  rrdatas = [
    google_sql_database_instance.db.ip_address[0].ip_address #IP van DB
  ]
}




resource "google_pubsub_topic" "new_hire" {
  name = "new-hire-events"
}

resource "google_pubsub_subscription" "orchestrator_sub" {
  name = "new-hire-orchestrator-sub"
  topic = google_pubsub_topic.new_hire.name
}

# GKE cluster
resource "kubernetes_service_account" "orchestrator" {
  metadata {
    name = "orchestrator-sa"
    namespace = kubernetes_namespace.platform.metadata[0].name
  }
}

resource "google_service_account" "gke_nodes" {
  account_id = "gke-nodes"
  display_name = "GKE Node Pool Service Account"
}

resource "google_project_iam_binding" "gke_nodes_artifact_registry" {
  project = var.project_id
  role = "roles/artifactregistry.reader"

  members = [
    "serviceAccount:${google_service_account.gke_nodes.email}"
  ]
}

resource "google_project_iam_binding" "gke_artifact_registry" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"

  members = [
    "serviceAccount:${google_container_node_pool.pool.node_config[0].service_account}"
  ]
}

resource "google_container_cluster" "gke" {
  name     = "platform-gke"
  location = var.zone   # ZONAL CLUSTER

  networking_mode = "VPC_NATIVE"

  network    = google_compute_network.vpc.self_link
  subnetwork = google_compute_subnetwork.subnet_gke.self_link

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  remove_default_node_pool = true
  initial_node_count       = 1

  release_channel {
    channel = "REGULAR"
  }

  deletion_protection = false

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "allow-all"
    }
  }

  depends_on = [
    kubernetes_service_account.orchestrator,
    google_sql_database_instance.db,
    google_sql_database.app,
    google_dns_record_set.db_a
  ]

}

resource "google_container_node_pool" "pool" {
  name = "platform-pool"
  location = var.zone
  cluster= google_container_cluster.gke.name
  node_count = 1

  node_config {
    machine_type = "e2-medium" # voor lagere kosten
    service_account = google_service_account.gke_nodes.email
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    tags = ["gke-node"]
  }
  
}
/*
resource "time_sleep" "wait_for_gke" {
  depends_on = [google_container_node_pool.pool]
  create_duration = "60s"
}*/

/*
# IAM
resource "google_project_iam_binding" "devs_viewer" {
  project = var.project_id
  role = "roles/viewer"

  members = [
    "user:${var.email}"
  ]
}

resource "google_project_iam_binding" "platform_admins" {
  project = var.project_id
  role = "roles/owner"

  members = [
    "user:${var.email}"
  ]
}
*/
# Logging
resource "google_bigquery_dataset" "logs" {
  dataset_id = "platform_logs"
  project = var.project_id
  location = "EU"
}

resource "google_logging_project_sink" "logs_to_bq" {
  name = "logs-to-bq"
  project = var.project_id
  destination = "bigquery.googleapis.com/projects/${var.project_id}/datasets/${google_bigquery_dataset.logs.dataset_id}"
  filter = "resource.type=k8s_container OR resource.type=gce_instance"

  unique_writer_identity = true
}

resource "google_storage_bucket" "app_data" {
  name = "${var.project_id}-app-data"
  location = "EU"
  storage_class = "STANDARD"
  uniform_bucket_level_access = true
}

resource "google_storage_bucket" "logs_archive" {
  name = "${var.project_id}-logs-archive"
  location = "EU"
  storage_class = "NEARLINE"
  uniform_bucket_level_access = true
}

data "google_client_config" "default" {}

data "google_container_cluster" "cluster" {
  name = google_container_cluster.gke.name
  location = var.zone
}

provider "kubernetes" {
  host                   = "https://${data.google_container_cluster.cluster.endpoint}"
  token                  = data.google_client_config.default.access_token
  cluster_ca_certificate = base64decode(data.google_container_cluster.cluster.master_auth[0].cluster_ca_certificate)


  load_config_file       = false
}
resource "google_service_account" "orchestrator_sa" {
  account_id = "orchestrator-sa"
  display_name = "Orchestrator Service Account"
  
  depends_on = [
    google_container_cluster.gke,
    google_container_node_pool.pool
  ]
}

resource "google_project_iam_binding" "orchestrator_sql_client" {
  project = var.project_id
  role = "roles/cloudsql.client"

  members = [
    "serviceAccount:${google_service_account.orchestrator_sa.email}",
  ]
}
# Self service portal
resource "kubernetes_namespace" "platform" {
  metadata {
    name = "platform"
  }
  depends_on = [
    google_container_cluster.gke,
    google_container_node_pool.pool
  ]
}

resource "kubernetes_deployment" "portal" {
  metadata {
    name = "self-service-portal"
    namespace = kubernetes_namespace.platform.metadata[0].name
    labels = { app = "portal" }
  }

  spec {
    replicas = 2

    selector {
      match_labels = { app = "portal" }
    }

    template {
      metadata { labels = { app = "portal" } }

      spec {
        container {
          name = "portal"
          image = "europe-west1-docker.pkg.dev/${var.project_id}/platform/portal:latest"
          port { container_port = 8080 }
        }
      }
    }
  }
}

resource "kubernetes_service" "portal_lb" {
  metadata {
    name = "portal-service"
    namespace = kubernetes_namespace.platform.metadata[0].name
  }

  #annotations = {"cloud.google.com/network-tier" = "Standard"}

  spec {
    selector = {
      app = "portal"
    }

    port {
      port = 80
      target_port = 8080
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_deployment" "orchestrator" {
  metadata {
    name = "provisioning-orchestrator"
    namespace = "platform"
    labels = {
      app = "provisioning-orchestrator"
    }
  }

  spec {
    replicas = 2

    selector {
      match_labels = {
        app = "provisioning-orchestrator"
      }
    }

    template {
      metadata {
        labels = {
          app = "provisioning-orchestrator"
        }
      }

      spec {
        service_account_name = kubernetes_service_account.orchestrator.metadata[0].name

        container {
          name  = "orchestrator"
          image = "europe-west1-docker.pkg.dev/${var.project_id}/platform/orchestrator:latest"

          env {
            name = "PROJECT_ID"
            value = var.project_id
          }

          env {
            name = "SUBSCRIPTION_ID"
            value = google_pubsub_subscription.orchestrator_sub.name
          }

          env {
            name = "DB_HOST"
            value = "app-db.db.internal"
          }

          env {
            name = "DB_PORT"
            value = "5432"
          }

          env {
            name = "DB_NAME"
            value = var.db_name
          }

          env {
            name = "DB_USER"
            value = var.db_user
          }

          env {
            name = "DB_PASSWORD"
            value = var.db_password
          }

          port {
            container_port = 8080
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_namespace.platform,
    kubernetes_service_account.orchestrator,
    google_sql_database_instance.db,
    google_dns_record_set.db_a
  ]
}

/*
resource "google_iam_workload_identity_pool_provider" "wi_provider" {
  workload_identity_pool_id = "github-pool"
  workload_identity_pool_provider_id = "gke-provider"

  oidc {
    issuer_uri = "https://container.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/clusters/${google_container_cluster.gke.name}"
  }

  attribute_mapping = {
    "google.subject" = "assertion.sub"
  }
}
*/
/*
resource "google_iam_workload_identity_pool" "wid_pool" {
  workload_identity_pool_id = "gke-pool"
}*/

/*
resource "google_iam_workload_identity_pool_provider" "wi_provider" {
  workload_identity_pool_id = google_iam_workload_identity_pool.wid_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "gke-provider"

  oidc {
    issuer_uri = "https://container.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/clusters/${google_container_cluster.gke.name}"
  }

  attribute_mapping = {
    "google.subject" = "assertion.sub"
  }
}
*/
