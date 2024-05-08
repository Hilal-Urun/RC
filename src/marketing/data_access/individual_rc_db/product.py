class Product:
    coll_name = 'products'

    def __init__(self, client, db_name):
        self.client = client
        self.db = self.client[db_name]
        self.coll = self.db[Product.coll_name]

    def get_products(self):
        products = self.coll.aggregate(
            [
                {
                    "$lookup": {
                        "from": "categories",
                        "localField": "category",
                        "foreignField": "_id",
                        "as": "category"
                    }
                },
                {
                    "$unwind": "$category"
                },
                {

                    "$lookup": {
                        "from": "catalogs",
                        "localField": "catalog",
                        "foreignField": "_id",
                        "as": "catalog"
                    }

                },
                {
                    "$unwind": "$catalog"
                },
                {
                    "$project": {
                        "_id": 1,
                        "title": 1,
                        "description": 1,
                        "ingredients": 1,
                        "allergens": 1,
                        "price": 1,
                        "category_name": "$category.name",
                        "catalog_name": "$catalog.name"
                    }
                }

            ]
        )
        return list(products)

    def get_menu_for_buyer_persona(self):
        products = self.get_products()
        menu = []
        for product in products:
            if (product.get('title', '') is not None or product.get('title', '') != "") and (product.get('price', '') is not None or product.get('price', '') != ""):
                menu.append(f"{product['title']}: {product['price']}")
        return menu


    def get_menu_as_list(self):
        products = self.get_products()
        menu = []
        for prod in products:
            menu.append({
                "Product_id": prod.get('_id', ''),
                "Product_name": prod.get('title', ''),
                "Product_description": prod.get('description', ''),
                "Product_ingredients": prod.get('ingredients', ''),
                "Product_allergens": prod.get('allergens', ''),
                "Product_category_name": prod.get('category_name', ''),
                "Product_catalog_name": prod.get('catalog_name', '')
            })
        return menu

    def get_menu_str(self):
        products = self.get_products()
        menu_str = ''
        # for product in products:
        #     product_str = f'''menu item with the following name: {product.get('title', '')} and the following
        #     description: {product.get('description', '')} and the following ingredients:
        #     {'&'.join(product.get('ingredients', []))} and the following allergens: {'&'.join(product.get('allergens', []))}
        #     this menu item called {product.get('title', '')} is belongs to the super category that called {product.get('category_name', '')}
        #     and in more specific to the following category that called {product.get('catalog_name', '')},
        #     '''
        #     menu_str += product_str

        category_groups = {}
        for product in products:
            category_name = product['category_name']
            if category_name not in category_groups:
                category_groups[category_name] = []
            category_groups[category_name].append(product['title'])

        menu_str = ""
        for category_name, product_list in category_groups.items():
            menu_str += f"Categoria : {category_name}\n"
            menu_str += f"Prodotti : {', '.join(product_list)}\n"
        return menu_str
