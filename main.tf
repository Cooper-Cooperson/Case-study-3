terraform {
  required_version = ">= 1.6.0"

  required_providers {
    kubernetes = {
      source = "hashicorp/kubernetes"
      version = "~> 2.25"
    }
  }
}

provider "google" {
  project = var.project_id
  region = var.region
  zone = var.zone
  impersonate_service_account = var.service_account
}

provider "google-beta" {
  project = var.project_id
  region = var.region
  impersonate_service_account = var.service_account
}

# VPC
resource "google_compute_network" "vpc" {
  name = "hub-vpc"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "subnet_gke" {
  name          = "subnet-gke"
  ip_cidr_range = "10.10.0.0/20"
  region        = var.region
  network       = google_compute_network.vpc.self_link

  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.11.0.0/20"
  }

  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.12.0.0/24"
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

  source_ranges = ["10.10.0.0/20"]   # GKE subnet var
  target_tags = ["cloud-sql"]      # SQL instance tag
}

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

# GKE cluster

resource "google_container_cluster" "gke" {
  name     = "platform-gke"
  location = var.region 

  network    = google_compute_network.vpc.self_link
  subnetwork = google_compute_subnetwork.subnet_gke.self_link

  remove_default_node_pool = true
  initial_node_count       = 1

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
    } 

  network_policy {
    enabled  = true
    provider = "CALICO"
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }

  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
}

resource "google_container_node_pool" "pool" {
  name = "platform-pool"
  location = var.region
  cluster= google_container_cluster.gke.name
  node_count = 3

  node_config {
    machine_type = "e2-standard-4"
    oauth_scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    tags = ["gke-node"]
  }
}
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

resource "google_sql_database_instance" "db" {
  name = "app-db"
  database_version = "POSTGRES_15"
  region = var.region
  deletion_protection = false
  depends_on = [
    google_service_networking_connection.private_vpc_connection
  ]

  settings {
    tier = "db-custom-2-7680"

    ip_configuration {
      ipv4_enabled = false
      private_network = google_compute_network.vpc.self_link
    }
  }
}

resource "google_sql_database" "db_default" {
  name = "appdb"
  instance = google_sql_database_instance.db.name
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
  location = var.region
}

provider "kubernetes" {
  host  = "https://${data.google_container_cluster.cluster.endpoint}"
  token = data.google_client_config.default.access_token

  cluster_ca_certificate = base64decode(
    data.google_container_cluster.cluster.master_auth[0].cluster_ca_certificate
  )
}

# Self service portal
resource "kubernetes_namespace" "platform" {
  metadata {
    name = "platform"
  }
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
          image = "europe-west4-docker.pkg.dev/${var.project_id}/platform/portal:latest"
          port { container_port = 8080 }
        }
      }
    }
  }
}

resource "google_service_account" "orchestrator_sa" {
  account_id = "orchestrator-sa"
  display_name = "Orchestrator Service Account"
}

resource "google_project_iam_binding" "orchestrator_sql" {
  project = var.project_id
  role = "roles/cloudsql.client"

  members = [
    "serviceAccount:${google_service_account.orchestrator_sa.email}"
  ]
}

resource "kubernetes_deployment" "orchestrator" {
  metadata {
    name = "provisioning-orchestrator"
    namespace = kubernetes_namespace.platform.metadata[0].name
    labels = { app = "orchestrator" }
  }

  spec {
    replicas = 2

    selector {
      match_labels = { app = "orchestrator" }
    }

    template {
  metadata { labels = { app = "orchestrator" } }

  spec {
    service_account_name = "orchestrator-sa"

    container {
      name = "orchestrator"
      image = "europe-west4-docker.pkg.dev/${var.project_id}/platform/orchestrator:latest"

      env {
        name = "PROJECT_ID"
        value = var.project_id
      }

      port { container_port = 8080 }
    }
  }
  }
  }
}

resource "google_iam_workload_identity_pool" "wip_pool" {
  workload_identity_pool_id = "gke-pool"
}

resource "google_iam_workload_identity_pool_provider" "wi_provider" {
  workload_identity_pool_id = google_iam_workload_identity_pool.wip_pool.workload_identity_pool_id
  workload_identity_pool_provider_id = "gke-provider"

  oidc {
    issuer_uri = "https://container.googleapis.com/v1/projects/${var.project_id}/locations/${var.region}/clusters/${google_container_cluster.gke.name}"
  }

  attribute_mapping = {
    "google.subject" = "assertion.sub"
  }
}