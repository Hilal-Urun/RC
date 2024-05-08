import re
import logging
import pandas as pd


def preprocess(description):
    """
    Input:
        description: Description of DataFrame
    Output:
        description: Basic preprocessed description of DataFrame.
    """
    if description:
        description = description.lower()
        description = re.sub(r"[\n\r]", " ", description)
        description = re.sub(r"\\n", " ", description)
        description = re.sub(r"\\r", " ", description)
        description = re.sub(r" +", " ",description)
        description = re.sub(r"[^\w\d\s,!?]", "", description)
        description = re.sub(r"\b[e]\b", ",", description)
        description = re.sub(r"\b[o]\b", ",", description)
        description = description.replace("informazioni", ",informazioni")
        description = description.split(",")
        description = [w.strip() for w in description]
        description = ", ".join(description)
    else:
        pass
    return description

def find_ingredients(description):
    """
    Input: 
        description: Description of DataFrame
    Output:
        Splitted description of DataFrame by comma.
    """
    if description:
        description =  description.split(",")
        description = [w.strip() for w in description]
        return description
    else:
        return []

def find_allergens(description):
    """
    Input:
        description: Description of DataFrame
    Output:
        allergen_list: Allergen list that created from description
    Definition:
        This function return allergen list by compare our description with allergen lists.
        If [word] of description in allergen list, take it.
    """
    glutine = ["cereale", "grani", "glutine", "cereali", "grano", "segale", "orzo", "avena", "farro", "kamut", "ibridati"]
    crostacei = ["crostacei", "gamberi", "scampi", "scampo", "aragoste", "aragosta", "granchi", "granchio", "paguro", "paguri"]
    uova = ["uova", "uovo", "maionese", "frittata", "emulsionanti", "pasta all’uovo", "biscotti", "torte", "torta", "gelato", "gelati", "crema", "creme"]
    pesce = ["pesce"]
    arachide = ["arachide"]
    soia = ["soia", "tofu"]
    latte = ["yogurt", "biscotto", "biscotti", "torta", "torte", "gelato", "gelati", "crema", "creme", "formaggio", "formaggi", "brie",
         "cheddar", "fita", "emmentaler", "manchego", "asiago", "bitto", "bra", "caciocavallo silano", "casciotta d’urbino",
         "castelmagno", "crescenza", "fiordilatte", "fiore sardo", "fontina", "gorgonzola", "grana padano", "mascarpone",
         "montasio", "mozzarella di bufala", "parmigiano reggiano", "pecorino", "pecorino romano", "provolone",
         "ragusano", "raschera", "ricotta", "robiola", "scamorza", "taleggio", "bitto", "bra", "caciocavallo silano", "casciotta d’urbino",
         "castelmagno", "crescenza", "fiordilatte", "fiore sardo", "fontina", "gorgonzola", "grana padano",
         "mascarpone", "montasio", "mozzarella di bufala", "parmigiano reggiano", "pecorino", "pecorino romano",
         "provolone", "ragusano", "raschera", "ricotta", "robiola", "scamorza", "taleggio", "mozzarella"]
    frutta_a_guscio = ["mandorle", "mandorla", "nocciola", "nocciole", "noci comuni", "noce di acagiù", "noce pecan", "noce del Brasile", "noce Queensland", "pistacchio", "pistacchi"]
    sedano = ["sedano"]
    senape = ["mostarda"]
    semi_di_sesamo = ["sesamo"]
    molluschi = ["canestrello", "cannolicchio", "capasanta", "cuore", "dattero di mare", "fasolaro", "garagolo", "lumachino", "cozza", "murice", "ostrica", "patella", "tartufo di mare", "tellina", "vongola"]

    it_allergens = glutine + crostacei + uova + pesce + arachide + soia + latte + frutta_a_guscio + sedano + senape + semi_di_sesamo + molluschi


    allergen_list = []
    description = re.sub(r"[^\w\d\s]", " ", description)
    for word in description.split():
        if word in it_allergens:
            if word in glutine:
                allergen_list.append("glutine")
            elif word in crostacei:
                allergen_list.append("crostacei")
            elif word in uova:
                allergen_list.append("uova")
            elif word in pesce:
                allergen_list.append("pesce")
            elif word in arachide:
                allergen_list.append("arachide")
            elif word in soia:
                allergen_list.append("soia")
            elif word in latte:
                allergen_list.append("latte")
            elif word in frutta_a_guscio:
                allergen_list.append("frutta a guscio")
            elif word in sedano:
                allergen_list.append("sedano")
            elif word in senape:
                allergen_list.append("senape")
            elif word in semi_di_sesamo:
                allergen_list.append("semi di sesamo")
            elif word in molluschi:
                allergen_list.append("molluschi")
            else:
                allergen_list.append("unknown")
        else:
            pass
    return list(set(allergen_list))

def get_allergens(
    json_data, 
    preprocess_column="description", 
    new_columns=["id", "title", "description"]
):
    """
    Input:
        json_data: JSON file
    Output:
        Dictionary: {ID_KEY: {name:n, description:d, ingredients:i, allergens:a }}
    Definition:
        This functions takes JSON for an input and creates dictionary of ingredients and allergens lists of that JSON file.
    """
    #language = json_data["language"]                    # language can be used for creating allergens lists. [it_IT, en_EN]
    #data = pd.DataFrame(json_data["items"]["items"])
    try:
        data = pd.DataFrame(json_data)                                                   # parsing JSON file to create DataFrame
        data = data[new_columns]                                                         # selecting DataFrame columns
        
        data["preprocessed_description"] = data[preprocess_column].apply(preprocess)     # calls preprocess() function
        data["ingredients"] = data["preprocessed_description"].apply(find_ingredients)   # calls find_ingredients() function 
        data["allergens"] = data["preprocessed_description"].apply(find_allergens)       # calls find_allergens() function
        data.drop_duplicates(subset="id", keep="first", inplace=True)
        data.set_index("id", inplace=True)                                               # set index to id of menu
        
        dict_data = data.to_dict("index")                                                # create dictionary of DataFrame
        
        items = []  
        for k,v in dict_data.items():
            v["id"] = k
            items.append(v)
    except Exception as e:
        logging.exception("")
        return e
    else:
        return items
