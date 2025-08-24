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
			# First try a query to see if the item exists and get its partition key
			print(f"[DEBUG] Querying for item in container '{container_name}' with id '{item_id}'")
			query = f"SELECT * FROM c WHERE c.id = '{item_id}'"
			items = list(container.query_items(query=query, enable_cross_partition_query=True))
			
			if items:
				print(f"[DEBUG] Found item via query: {items[0]}")
				# Use the first found item's id as partition key if none provided
				partition_key = partition_key or items[0].get('id')
				print(f"[DEBUG] Using partition key: {partition_key}")
				return items[0]
			
			print(f"[DEBUG] No items found via query, attempting direct read")
			result = container.read_item(item=item_id, partition_key=partition_key or item_id)
			print(f"[DEBUG] Successfully retrieved item via direct read: {result}")
			return result
			
		except exceptions.CosmosResourceNotFoundError as e:
			print(f"[DEBUG] Item not found. Error: {str(e)}")
			return None
		except Exception as e:
			print(f"[DEBUG] Unexpected error reading item: {str(e)}")
			print(f"[DEBUG] Container name: {container_name}")
			print(f"[DEBUG] Database name: {self.database_name}")
			print(f"[DEBUG] Connection string endpoint: {self.connection_string.split(';')[0]}")
			raise

	def query_items(self, container_name, query, parameters=None):
		container = self.get_container(container_name)
		return list(container.query_items(query=query, parameters=parameters or [], enable_cross_partition_query=True))

	def upsert_item(self, container_name, item):
		container = self.get_container(container_name)
		return container.upsert_item(item)
