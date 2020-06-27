class User():
    def __init__(self, db, collection):
        self.db = db
        self.collection = collection

    def create_new_user(self, access_key, access_secret, user_id):
        doc = {}
        user_id = int(user_id)
        doc["user_id"] = user_id
        doc["access_key"] = access_key
        doc["access_secret"] = access_secret
        # elem = self.collection.find({}, {"name": name})
        x = self.collection.insert_one(doc)

    def delete_user(self, user_id):
        user_id = int(user_id)
        self.collection.delete_one({ "user_id": user_id })

    def find_user(self, user_id):
        user_id = int(user_id)
        return self.collection.find_one({ "user_id": user_id }, { "user_id": 1, "access_key": 1, "access_secret": 1 })