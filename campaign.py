class Campaign():
    def __init__(self, db, collection):
        self.db = db
        self.collection = collection

    def create_new_campaign(self, id, name, strategy, followers, started, message):
        doc = {}
        doc["id"] = id
        doc["name"] = name
        doc["strategy"] = strategy
        doc["followers"] = followers
        doc["started"] = started
        doc["message"] = message
        elem = self.collection.find({}, {"name": name})
        x = self.collection.insert_one(doc)
        
    def start_campaign(self, id):
        count = self.collection.count_documents({ "id": id })
        if count > 0:
            self.collection.update_one({ "id": id }, { "$set": { "started": True }})

    def stop_campaign(self, id):
        count = self.collection.count_documents({ "id": id })
        if count > 0:
            self.collection.update_one({ "id": id }, { "$set": { "started": False }})

    def is_started(self, id):
        l = self.collection.find_one({"id": id}, { "started": 1 })
        return l["started"]

    def get_status(self, id):
        cp = self.collection.find_one({ "id": id })
        count = sum(1 for i in cp["followers"] if i["sent"])
        return { "sent": count, "total": len(cp["followers"]), "started": cp["started"] }

    def truncate(self):
        self.collection.drop()

    def delete(self, id):
        self.collection.delete_one({ "id": id })

    def list_all(self):
        l = self.collection.find({}, { "_id": 0, "id": 1, "name": 1, "strategy": 1, "started": 1, "message": 1 })
        return l

    def get_campaign(self, id):
        c = self.collection.find_one({ "id": id })
        return c

    def mark_sent(self, cid, uid):
        self.collection.update_one( { "id": cid, "followers.id": uid }, { "$set": { "followers.$.sent": True } } )

    def id_exists(self, id):
        count = self.collection.count_documents({ "id": id })
        return (count >= 1)

    def reset_sent(self, id):
        self.collection.update_many( { "id": id }, { "$set": { "followers.$[].sent": False, "started": False } } )

    def edit_name(self, id, name):
        self.collection.update_one( { "id": id }, { "$set": { "name": name } } )

    def edit_message(self, id, message):
        self.collection.update_one( { "id": id }, { "$set": { "message": message } } )
