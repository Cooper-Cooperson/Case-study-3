terraform {
  backend "gcs" {
    bucket = "project-96521d1d-c0a7-4c19-b4c-terraform-state"
    prefix = "env/default"
  }
}
