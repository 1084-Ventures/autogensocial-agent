import os
from azure.cosmos import CosmosClient, exceptions

class CosmosDBClient:
	def __init__(self):
		# Get environment variables (for local dev, these are in local.settings.json)
		self.connection_string = os.environ.get("COSMOS_DB_CONNECTION_STRING")
		self.database_name = os.environ.get("COSMOS_DB_NAME")
		if not self.connection_string or not self.database_name:
			raise ValueError("Missing Cosmos DB connection string or database name in environment variables.")
		self.client = CosmosClient.from_connection_string(self.connection_string)
		self.database = self.client.get_database_client(self.database_name)

	def get_container(self, container_name):
		return self.database.get_container_client(container_name)

	def get_item(self, container_name, item_id, partition_key=None):
		container = self.get_container(container_name)
		try:
			return container.read_item(item=item_id, partition_key=partition_key or item_id)
		except exceptions.CosmosResourceNotFoundError:
			return None

	def query_items(self, container_name, query, parameters=None):
		container = self.get_container(container_name)
		return list(container.query_items(query=query, parameters=parameters or [], enable_cross_partition_query=True))

	def upsert_item(self, container_name, item):
		container = self.get_container(container_name)
		return container.upsert_item(item)
