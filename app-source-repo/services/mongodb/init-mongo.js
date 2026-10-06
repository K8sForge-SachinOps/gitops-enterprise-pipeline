db = db.getSiblingDB('enterprise_db');

db.createCollection('deployments');
db.deployments.insertOne({
    service: "gitops-pipeline",
    environment: "dev",
    timestamp: new Date(),
    status: "initialized",
    compliance: "State Data Centre SDC-01"
});

print(">> [MongoDB-Init] Enterprise database and initial collections seeded.");
