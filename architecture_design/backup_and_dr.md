# Backup & Disaster Recovery Plan
- **Databases:** Use AWS RDS Multi-AZ for PostgreSQL (automatic failover). Enable daily snapshots, point-in-time recovery (up to 35 days). Test restore procedures regularly.  
- **Storage:** S3 objects in bucket with versioning enabled. Enable cross-region replication (to another AWS region) for DR.  
- **Kubernetes:** Store manifests in Git. In case of cluster loss, redeploy via IaC (Terraform/CDK). 
- **Regional DR:** For critical systems, deploy second cluster in a separate region (active-active or warm standby). Use Route53 failover DNS.  
- **Offsite:** Maintain periodic offsite backups of source data (e.g. daily export of projects JSON to another cloud).  
- **Recovery Time (RTO/RPO):** Aim for RTO < 4 hours, RPO < 15 minutes for Phase 1 data.  
Test DR drills yearly: e.g. simulate the loss of a region, restore from backups, and measure recovery.
