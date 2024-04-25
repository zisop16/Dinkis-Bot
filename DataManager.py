from pymongo import MongoClient

class DataManager:
    def __init__(self, password):
        api_url = f"mongodb+srv://p0six:{password}@cluster0.e7vueuh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
        cluster = MongoClient(api_url)
        db = cluster["NationsDiscord"]
        self.user_data = db["UserData"]
        self.server_data = db["ServerData"]
    
    def get_user(self, user_id):
        result = self.user_data.find_one({"_id": user_id})
        return result
    
    def user_exists(self, user_id):
        return self.get_user(user_id) is not None
    
    def add_user(self, user_id):
        post = {
            "_id": user_id,
            "warnings": 0
        }
        self.user_data.insert_one(post)

    def add_warning(self, user_id):
        query = {"_id": user_id}
        command = {
            "$inc": {
                "warnings": 1
            }
        }
        self.user_data.update_one(query, command)

    def get_warnings(self, user_id):
        data = self.get_user(user_id)
        warnings = data["warnings"]
        return warnings

    def safe_add(self, user_id):
        if not self.get_user(user_id):
            self.add_user(user_id)