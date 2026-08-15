# Cost & Infrastructure Estimates
Using a **cloud-first model (AWS/GCP)**:  
- **Compute:** For Phase 1 MVP: estimate 3–5 microservices. Use Fargate/EKS on t3.small (2 vCPU) for each. On-demand Linux t3: ~$0.05/vCPU-hour. For 2 vCPUs => ~$0.10/hr (~$72/mo per instance). If 5 services, ~ $360/mo.  
- **Database:** PostgreSQL db.t3.medium (2 vCPU, 4GB RAM) in Multi-AZ: ~$50/mo.  
- **Storage:** S3 for models (e.g. 100GB) ~ $2/mo.  
- **Networking:** Data transfer and ELB costs (~$20/mo).  
- **Monitoring/Log:** CloudWatch/Prometheus (low if data small).  
- **Extra:** AWS SNS, SQS, Secrets Manager (modest).  
Total Phase 1 monthly on AWS roughly **$500–$800** (development/staging smaller). Scale up: Phase 2+ may need larger DB, more replicas.  
Costs will be revised per traffic – consider savings plans or spot instances for cost optimization.  
(Exact prices updated from AWS pricing pages).
