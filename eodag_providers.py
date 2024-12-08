from eodag import EODataAccessGateway

dag = EODataAccessGateway()
providers = dag.available_providers()
print(providers)
