from datetime import datetime, timedelta
import numpy as np


def tag_users(events):
    today = datetime.today()
    past_1_hour = today - timedelta(hours=1)
    past_7_days = today - timedelta(days=7)
    past_30_days = today - timedelta(days=30)
    past_3_months = today - timedelta(days=90)
    past_six_months = today - timedelta(days=180)
    past_year = today - timedelta(days=365)

    tags = {}
    # Tag users who purchased at least in the past 6 months not in 30 days !
    purchased_in_past_six_months = list()
    for event in events:
        if event['type'] == 'Purchase' and past_six_months < event['timestamp'] < past_30_days:
            purchased_in_past_six_months.append(event['user_id'])
    tags['acquistato negli ultimi 6 mesi'] = purchased_in_past_six_months

    # Tag users who purchased sth in the past 30 days
    purchased_in_past_30_days = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_30_days:
            purchased_in_past_30_days.append(event['user_id'])
    tags['acquistato negli ultimi 30 giorni'] = purchased_in_past_30_days

    # Tag users who made at least 2 purchase in the past 6 months not made at least 2 purchases in past 30 days
    multiple_purchases_in_past_six_months = list()
    for user_id in purchased_in_past_six_months:
        purchase_count = sum(1 for event in events if
                             event['type'] == 'Purchase' and event['user_id'] == user_id and past_six_months < event[
                                 'timestamp'] < past_30_days)
        if purchase_count >= 2:
            multiple_purchases_in_past_six_months.append(user_id)
    tags['acquisti multipli negli ultimi 6 mesi'] = multiple_purchases_in_past_six_months

    # Tag users who made at least 2 purchases in the past 30 days
    multiple_purchases_in_past_30_days = list()
    for user_id in purchased_in_past_30_days:
        purchase_count = sum(1 for event in events if
                             event['type'] == 'Purchase' and event['user_id'] == user_id and event[
                                 'timestamp'] > past_30_days)
        if purchase_count >= 2:
            multiple_purchases_in_past_30_days.append(user_id)
    tags['acquisti multipli negli ultimi 30 giorni'] = multiple_purchases_in_past_30_days

    # Tag users who made a purchase in the past 6 months but not in the past 3 months
    purchased_in_past_6_months_not_in_past_3_months = list()
    for user_id in purchased_in_past_six_months:
        recent_purchase_count = sum(1 for event in events if
                                    event['type'] == 'Purchase' and event['user_id'] == user_id and event[
                                        'timestamp'] > past_3_months)
        if recent_purchase_count == 0:
            purchased_in_past_6_months_not_in_past_3_months.append(user_id)
    tags['nessun acquisto negli ultimi 3 mesi'] = purchased_in_past_6_months_not_in_past_3_months

    # Tag users who completed at least 7 purchases in the past year
    loyal_shoppers = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_year:
            user_id = event['user_id']
            if sum(1 for e in events if
                   e['type'] == 'Purchase' and e['user_id'] == user_id and e['timestamp'] > past_year) >= 7:
                loyal_shoppers.append(user_id)
    tags['fedele'] = loyal_shoppers

    # Tag users who completed at least 5 purchases in the past 6 months (abituale)
    frequent_buyers = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months:
            user_id = event['user_id']
            if sum(1 for e in events if
                   e['type'] == 'Purchase' and e['user_id'] == user_id and e['timestamp'] > past_six_months) >= 5:
                frequent_buyers.append(user_id)
    tags['abituale'] = frequent_buyers



    # Tag users who completed a purchase using a coupon in the past 30 days AND used at least 2 coupons
    coupon_lovers = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_30_days and event['discount_type'] == 'Coupon':
            user_id = event['user_id']
            coupon_count = sum(1 for e in events if
                               e['type'] == 'Purchase' and e['user_id'] == user_id and e['timestamp'] > past_30_days and
                               e['discount_type'] == 'Coupon')
            discount_usage_count = sum(1 for e in events if
                                       e['type'] == 'Discount Usage' and e['user_id'] == user_id and e[
                                           'timestamp'] > past_30_days)
            if coupon_count >= 1 and discount_usage_count >= 2:
                coupon_lovers.append(user_id)
    tags['amante degli sconti'] = coupon_lovers

    # Tag users who completed a purchase using a flat coupon in the past 6 months and have redeemed at least 2 flat coupons
    bought_items_with_flat_discount = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months:
            user_id = event['user_id']
            flat_coupon_count = sum(1 for e in events if
                                    e['type'] == 'Flat Coupon Used' and e['user_id'] == user_id and e[
                                        'timestamp'] > past_six_months)
            if flat_coupon_count >= 2:
                bought_items_with_flat_discount.append(user_id)
    tags['amante degli sconti fissi'] = bought_items_with_flat_discount

    # Tag users who purchased a bundle in the past 6 months
    purchased_bundle_in_past_six_months = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months and event.get(
                'Product Purchase Category') == 'bundle' and event.get('Purchase') >= 2:
            purchased_bundle_in_past_six_months.append(event['user_id'])
    tags['amante dei bundle'] = purchased_bundle_in_past_six_months

    # Tag users who purchased a fixed menu in the past 6 months
    purchased_fixed_menu_in_past_six_months = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months and event.get(
                'Product Purchase Category') == 'fixed menu' and event.get('Purchase') >= 2:
            purchased_fixed_menu_in_past_six_months.append(event['user_id'])
    tags['amante dei menù fissi'] = purchased_fixed_menu_in_past_six_months

    # Tag users who purchased a special menu in the past 6 months
    purchased_special_menu_in_past_six_months = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months and event.get(
                'Product Purchase Category') == 'special menu' and event.get('Purchase') >= 2:
            purchased_special_menu_in_past_six_months.append(event['user_id'])
    tags['amante dei menù speciali '] = purchased_special_menu_in_past_six_months

    # Tag users who made multiple purchases in a specific category in the past year
    # category name will come from db dynamicly
    # TODO IMPLEMENTATI0N OF "acquisti multipli nella categoria <category name>" TAG

    # Tag the highest spending users in a specific category
    # TODO IMPLEMENTATION OF "VIP della categoria <category name>" TAG, x will come from db --- ALESSIO


    # Tag users who conducted a search and completed a purchase during the same session

    # CHECK AGAIN!!
    search_and_purchase = list()
    for user_id in set(event['user_id'] for event in events if event['type'] == 'Search' and event['value'] >= 2):
        if any(event['type'] == 'Purchase' and event['session_id'] == event2['session_id'] for event in events for
               event2 in events if event['user_id'] == user_id and event2['user_id'] == user_id):
            search_and_purchase.append(user_id)
    tags['amante dei menù speciali'] = search_and_purchase

    # Tag users who completed a purchase with a value of over 15% above the average purchase value
    # <Purchase> event value is above ‘$X’ AND event is at least ‘1’ time + NEED TO HAVE AT LEAST 50 CLIENTS
    # TODO X LOOK AGAIN?
    purchase_values = [event['value'] for event in events if event['type'] == 'Purchase']
    if len(purchase_values) >= 50:
        avg_purchase_value = sum(purchase_values) / len(purchase_values)
        big_spenders = set(event['user_id'] for event in events if
                           event['type'] == 'Purchase' and event['value'] > 1.15 * avg_purchase_value)
        tags['alto spendente'] = big_spenders

        # Tag users whose Lifetime value exceeds X amount
        # TODO X life time avg
        lifetime_values = {}
        for event in events:
            if event['type'] == 'Purchase':
                if event['user_id'] not in lifetime_values:
                    lifetime_values[event['user_id']] = 0
                lifetime_values[event['user_id']] += event['value']
        vip_shoppers = set(
            user_id for user_id in lifetime_values if lifetime_values[user_id] >= 10000 and len(lifetime_values) >= 50)
        tags['VIP'] = vip_shoppers

        # Tag users with items in their shopping carts from previous sessions but without any purchases
    abandoned_carts = list()
    for user_id in set(event['user_id'] for event in events if event['type'] == 'Add to Cart'):
        if all(event['type'] != 'Purchase' for event in events if
               event['user_id'] == user_id and event['timestamp'] > past_7_days):
            abandoned_carts.append(user_id)
    tags['carrello abbandonato'] = abandoned_carts

    # Tag users who completed a purchase during a relatively short time
    # TODO X 15 MİN  FİX İT
    product_focused_shoppers = set(event['user_id'] for event in events if
                                   event['type'] == 'Purchase' and event['value'] >= 1 and event[
                                       'time_to_purchase'] <= past_1_hour)
    tags.append(('cliente deciso', product_focused_shoppers))

    # Tag users as "Browsers" if they spend a relatively great deal of time on the site
    browsers = list()
    for user_id in set(event['user_id'] for event in events):
        session_count = sum(1 for event in events if event['type'] == 'Session' and event['user_id'] == user_id)
        total_session_time = sum(
            event['duration'] for event in events if event['type'] == 'Session' and event['user_id'] == user_id)
        average_session_time = total_session_time / session_count if session_count > 0 else 0
        if average_session_time > np.percentile(
                [event['duration'] for event in events if event['type'] == 'Session'], 95) and \
                sum(1 for event in events if event['type'] == 'Purchase' and event['user_id'] == user_id) == 0:
            browsers.append(user_id)
    tags['cliente tranquillo'] = browsers

    # Tag users as "Researchers" if they spend a lot of time exploring a specific product page
    researchers = list()
    for user_id in set(event['user_id'] for event in events):
        product_page_views = [event for event in events if
                              event['type'] == 'Page View' and 'Product Pages' in event['page_type'] and event[
                                  'user_id'] == user_id]
        if len(product_page_views) > 0 and \
                np.mean([event['duration'] for event in product_page_views]) > np.percentile(
            [event['duration'] for event in product_page_views], 75) and \
                sum(1 for event in events if
                    event['type'] == 'Session' and event['user_id'] == user_id and 'Product Pages' in event[
                        'page_type'] and event['pages_per_session'] <= 3) > 0:
            researchers.append(user_id)
    tags['ricercatore'] = researchers

    # Tag users as "Bargain Hunters" if they are on the lookout for the best available deals
    bargain_hunters = list()
    for user_id in set(event['user_id'] for event in events):
        category_sorting_type_count = sum(1 for event in events if event['type'] == 'Category Sorting' and event[
            'user_id'] == user_id and 'Price: Low to High' in event['sorting_type'])
        on_sale_page_views_count = sum(1 for event in events if
                                       event['type'] == 'Page View' and event['user_id'] == user_id and event[
                                           'page_visited'] == '/on-sale/')
        if category_sorting_type_count + on_sale_page_views_count >= 5:
            bargain_hunters.append(user_id)
    tags['cacciatore di affari'] = bargain_hunters

    # Tag one-time shoppers who completed a purchase during the past 6 months
    one_time_shoppers = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_six_months and event['sessions_per_user'] == 1:
            one_time_shoppers.append(event['user_id'])
    tags['da reingaggiare'] = one_time_shoppers

    # Tag maximizers who browse entire product category before making a decision
    maximizers = list()
    for event in events:
        if event['pages_per_session'] >= 3 and event['viewed_page_type'] == 'category pages' and event[
            'event'] == 'reached category end':
            maximizers.append(event['user_id'])
    tags['razionale'] = maximizers

    # Tag impulsivo buyers who completed a purchase during the past 30 days

    impulsivo_buyers = list()
    for event in events:
        if event['type'] == 'Purchase' and event['timestamp'] > past_30_days and event['sessions_per_user'] == 1:
            if event['user_id'] not in (maximizers, browsers, researchers):
                impulsivo_buyers.append(event['user_id'])
    tags['impulsivo'] = impulsivo_buyers

    # Tag delivery customers who only made delivery purchases
    delivery_customers = list()
    for event in events:
        if event['delivery_purchase'] >= 1 and event['event_type'] != 'Reservation':
            delivery_customers.append(event['user_id'])
    tags['preferisce delivery'] = delivery_customers

    # Tag users who only made table reservations
    table_reservation_users = list()
    for event in events:
        if event['type'] == 'Reservation' and event['timestamp'] > past_six_months:
            if not event['delivery']:
                table_reservation_users.append(event['user_id'])
    tags['preferisce mangiare al tavolo'] = table_reservation_users

    # Tag users who registered for the newsletter
    newsletter_users = list()
    for event in events:
        if event['type'] == 'Event' and event['event_name'] == 'newsletter signup':
            newsletter_users.append(event['user_id'])
    tags['registrato alla newsletter'] = newsletter_users

    # Tag users who visited the menu page via QR Code
    qr_code_users = list()
    for event in events:
        if event['type'] == 'Page Visit' and event['utm_source'] == 'qr_code' and event['timestamp'] > past_six_months:
            qr_code_users.append(event['user_id'])
    tags['cliente del ristorante'] = qr_code_users

    return tags
