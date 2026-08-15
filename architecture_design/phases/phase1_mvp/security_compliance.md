# Phase 1 Security/Compliance
- **Input Validation:** All API inputs use Pydantic schemas (reject invalid, no SQL injection).  
- **Auth:** JWT + password hashing, HTTPS enforced.  
- **Data Protection:** Only authenticated users can see their projects.  
- **Compliance:** If storing any personal data (email), comply with privacy laws.
