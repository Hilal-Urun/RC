from collections import Counter
import numpy as np
import pymongo
from bson import ObjectId
from marketing import db_rc_pharmacies, db
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from marketing.data_access.individual_rc_db.product import Product


class temporary_recommendation_to_users:
    def __int__(self, restaurant_id, product_ids=None):
        self.restaurant_id = restaurant_id
        self.product_ids = product_ids if isinstance(product_ids, list) else [product_ids]

    def similar_products_recommended(self):
        rest_menu = Product(db_rc_pharmacies, self.restaurant_id)
        menu = rest_menu.get_menu_as_list()

        product_descriptions = [
            ", ".join(
                [product['Product_description'], str(product['Product_ingredients']), str(product['Product_allergens']),
                 str(product['Product_category_name']), str(product['Product_catalog_name'])]) for product in menu]

        tfidf_vectorizer = TfidfVectorizer()
        tfidf_matrix = tfidf_vectorizer.fit_transform(product_descriptions)
        product_similarity_matrix = cosine_similarity(tfidf_matrix, tfidf_matrix)

        product_indices = [menu.index(product) for product in menu if product['Product_id'] in self.product_ids]
        product_similarity_matrix[np.isnan(product_similarity_matrix)] = 0
        average_similarity = product_similarity_matrix[product_indices].mean(axis=0)
        similar_product_indices = average_similarity.argsort()[::-1][1:5]

        similar_product_ids = [str(menu[index]['Product_id']) for index in similar_product_indices]

        return similar_product_ids


class product_recommendation_to_users:
    def __init__(self, restaurant_id, user_id=None, product_ids=None):
        self.restaurant_id = restaurant_id
        self.user_id = user_id
        self.product_ids = product_ids if isinstance(product_ids, list) else [product_ids]
        self.restaurant_db = db_rc_pharmacies[restaurant_id]

    def recommend_from_user_history(self):
        suggested_products = []
        try:
            user = list((self.restaurant_db["customers"]).find({"centralCustomerId": self.user_id}))[0]
            if user and "orders" in user:
                query = {"_id": {"$in": user["orders"]}}
                # fetch product ids ordered before
                ordered_products = list(db_rc_pharmacies[self.restaurant_id]["products"].find(query))
                # extract ordered product categories
                category_ids = [doc['category'] for doc in ordered_products]
                for category_id in category_ids:
                    # Fetch products within the current category
                    category_products = list(
                        db_rc_pharmacies[self.restaurant_id]["products"].find({"category": category_id}))
                    # Sort the products within the category based on 'productOrder'
                    category_products.sort(key=lambda x: x['productOrder'])
                    # Extend the suggested products list with the sorted products
                    suggested_products.extend(category_products)
            suggested_products.sort(key=lambda x: x['productOrder'])
            product_ids = [str(product['_id']) for product in suggested_products[:3]]
            return product_ids
        except:
            return suggested_products

    def recommend_popular_products(self):
        try:
            popular_products = list(self.restaurant_db.products.find().sort("productOrder",
                                                                            pymongo.DESCENDING).limit(3))

            popular_product_ids = [str(product['_id']) for product in popular_products]
            return popular_product_ids
        except:
            return []

    def recommend_frequently_bought_together(self):
        frequently_bought_together = []
        try:
            orders_with_products = list(self.restaurant_db.customers.find(
                {"orders": {"$in": [ObjectId(p) for p in self.product_ids]}}))
            for order in orders_with_products:
                for product in order.get("orders", []):
                    if product not in self.product_ids:
                        frequently_bought_together.append(product)
            product_count = Counter(frequently_bought_together)
            sorted_products = sorted(product_count.items(), key=lambda x: x[1], reverse=True)[:3]
            frequently_bought_together_products = [str(item[0]) for item in sorted_products]
            return frequently_bought_together_products
        except:
            return frequently_bought_together

    def final_recommendation(self):
        recommended_product_ids = list(
            set(self.recommend_from_user_history() + self.recommend_popular_products() + self.recommend_frequently_bought_together()))
        if len(recommended_product_ids) == 0:
            temp_rec = temporary_recommendation_to_users()
            temp_rec.restaurant_id = self.restaurant_id
            temp_rec.product_ids = self.product_ids
            recommended_product_ids = temp_rec.similar_products_recommended()
        return recommended_product_ids
