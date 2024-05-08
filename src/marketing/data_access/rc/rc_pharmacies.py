import logging
from bson import ObjectId
from marketing import db_rc_pharmacies
from marketing.data_access.individual_rc_db.product import Product

"""NOTE : DB INSTANCE IS ROOT, IF YOU WANT TO ACCESS rc DB TRY db_rc_pharmacies["rc"]
   or individual db try db_rc_pharmacies[restaurant_id][collection]
"""


class RestaurantInfoRetriever:
    def __init__(self, restaurant_id):
        self.restaurant_id = restaurant_id

    def get_restaurant_info_by_id(self):
        query = {"pharmacyOwner": ObjectId(self.restaurant_id)}
        restaurant_info = db_rc_pharmacies["rc"]["pharmacies"].find_one(query)
        if restaurant_info is not None:
            output = {
                "name": restaurant_info.get('name', ''),
                "category": restaurant_info.get("category", ''),
                "website": restaurant_info.get('domain', ''),
                "place_id": restaurant_info['place']['result'].get('place_id', ''),
                "opening_hours": ", ".join(restaurant_info['place']['openingHours'].get('weekday_text', '')),
            }

            restaurant_info_restaurantdatas = db_rc_pharmacies[self.restaurant_id]["restaurantdatas"].find_one({})
            output.update({
                "whatsapp": restaurant_info_restaurantdatas.get("whatsapp_number", ""),
                "phone_number": restaurant_info_restaurantdatas.get("formatted_phone_number", ""),
                "address": restaurant_info_restaurantdatas.get("formatted_address", ""),
            })

            restaurant_menu = Product(db_rc_pharmacies, self.restaurant_id)
            restaurant_menu_str = restaurant_menu.get_menu_str()
            output.update({"menu": restaurant_menu_str})

            return output
        else:
            msg = f"Restaurant {self.restaurant_id} does not exist!"
            logging.exception(msg)
            return {"response": msg}
