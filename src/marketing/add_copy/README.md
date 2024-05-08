## AD_Copy <img width="35" alt="Ad_banner" src="https://user-images.githubusercontent.com/23742278/205077505-1e47c43e-7890-4ac8-a4d9-7ea3d6d7e15d.png"> 

Is a built-in funtion in the Marketing module that let the business owner create an ad template to proceed with the marketing compaign easily. Within this funtion, the owner can choose to create ads in different templates, so you don't waste time to choose the right keywords that fits the needs. For each ad goals, there are a pre-existed senteces that's ready to be used in the campaign.

Some comination of the templates are:

| Feature | Description |
| ------------ | ----------- |
| **Template&nbsp;1** | Let you create a template that has the business website, phone number, and social media account of the business |
| **Template&nbsp;2** | Let you create a template that has the address, hours, reservation link, business website, phone number, and social media account of the business |
| **Template&nbsp;3** | Let you create a template that has the address, hours, reservation link, business website, phone number, and social media account of the business |
| **Template&nbsp;4** | Let you create a template that has the address, hours, and phone number of the business |


## Methodology

The templates are created from [`class createTemplates`](https://github.com/AiGotsrl/MS-DSMarketing/blob/7be695ec1932bc210e30c53d04f63a23ce2b3ee9/src/marketing/add_copy/addGeneration.py#L222) with the help  of [`class addChooser`](https://github.com/AiGotsrl/MS-DSMarketing/blob/7be695ec1932bc210e30c53d04f63a23ce2b3ee9/src/marketing/add_copy/addGeneration.py#L47) to construct the templates with the already existed example sentences that's available in the data file [`Data Folder`](https://github.com/AiGotsrl/MS-DSMarketing/tree/develop/src/marketing/add_copy/data) to be used to generate an ad for the campaign.

Within the `class addChooser`, there some funtions that from which, the template is choosen randomly. The following are the functions within the class:

```py

# This funtion randomly choose example sentences from the data file related to the CTAs
def choose_from_cta(self):

# This funtion randomly choose example sentences from the data file if the the website 
# needed to be mentioned in the compaign
def choose_from_website(self):

# This funtion randomly choose example sentences from the data file depending on either 
# telephone number or Whatsapp exist or both
def choose_from_phone(self, has_phone, has_whatsapp):
 
# This funtion randomly choose example sentences from the data file depengin on either 
# Facebook or Instagram exist or both
def choose_from_socialMedia(self, has_facebook, has_instagram):

# This funtion randomly choose example sentences from the data file if the opening hours 
# needs to be mentioned in the compaign
def choose_from_workingHours(self, hours, days):

# This funtion randomly choose example sentences from the data file if the owner 
# wants to mention the address of the business
def choose_from_address(self):

# This funtion randomly choose example sentences from the data file if the wants customers
# reserve an online reservation.
def choose_from_reversation(self):

# This funtion randomly choose example sentences from the data file if the owner 
# has an onlien delivery option
def choose_from_delivery(self):

```

## Extras

To create an ad more in a funky way, the [`emoji funtion`](https://github.com/AiGotsrl/MS-DSMarketing/blob/7be695ec1932bc210e30c53d04f63a23ce2b3ee9/src/marketing/add_copy/addGeneration.py#L43) is added. This funtion takes a specific tag and convert it to an specific emoji depending on the converted tag. It uses the script [`replace_tags.py`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/add_copy/replace_tags.py) to do the replacement. The List of tags related emojis are found in [`congif.yml`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/add_copy/config.yml).


##

<sub> Copyright &copy; Restaurants Club All right reserved <sub>
