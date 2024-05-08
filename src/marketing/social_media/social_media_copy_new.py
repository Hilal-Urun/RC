from marketing.data_access.rc.rc_pharmacies import RestaurantInfoRetriever
from marketing.shared import get_completion, extract_hashtags_return_text2


class SocialMediaCopy:
    def __init__(self, goal, user_id):
        self.goal = goal
        self.user_id = user_id
        retriever = RestaurantInfoRetriever(restaurant_id=user_id)
        restaurant_info = retriever.get_restaurant_info_by_id()
        self.name = restaurant_info.get("name")
        #self.primary_cat = restaurant_info["category"]
        self.website = restaurant_info.get("website")
        self.whatsapp = restaurant_info.get("whatsapp")
        self.phone_number = restaurant_info.get("phone_number")
        self.open_hours = restaurant_info.get("opening_hours")
        self.address = restaurant_info.get("address")
        self.menu = restaurant_info.get("menu")

    def create_prompt(self,additinal_prompt):
        prompt = f"Sei il social media manager del ristorante {self.name}\. Crea una descrizione per il post settimanale della pagina Facebook e Instagram del ristorante.\
          Linee Guida:\
          - L'obiettivo di questo post è {self.goal}.\
          - {additinal_prompt}\
          - Usa tra 3-5 emoji. Non più di una emoji ogni due frasi.\
          - Cita sempre massimo 1 o 2 prodotti dal menù. Questo è il menù: {self.menu}\
          - Ricordati che un post social media fa parte di un piano di contenuti, non è un contenuto sponsorizzato. L'approccio quindi deve essere improntato alla valorizzazione dei punti di forza del ristorante e non a una conversione diretta.  \
          - Nella Call to Action puoi citare sempre una informazione tra: gli orari di apertura ({self.open_hours}), indirizzo del ristorante ({self.address}), numero di telefono ({self.phone_number}) o quando non è vuoto il numero di whatsapp ({self.whatsapp}).\
          - Ricorda che il ristorante ha un menù online sul sito web, visitabile all'indirizzo  www.{self.website}/menu \
          - Puoi inserire hashtag alla fine della descrizione, correlati con il testo e obiettivo. Aggiungili usando il simbolo #."
        return prompt

    def complete_text(self,additinal_prompt):
        prompt = self.create_prompt(additinal_prompt)
        text = get_completion(prompt,temperature=0.8)
        hashtags, text=extract_hashtags_return_text2(text)
        return {"text":text,"hashtags":hashtags}
