## Custom Audience <img width="30" alt="Screenshot_2022-11-28_at_13 49 14-removebg-preview" src="https://user-images.githubusercontent.com/23742278/205693136-568ae602-f6b2-4a5b-b4a5-712cb7311abc.png">


To have an insight on the trafficing of the busniess campaign ads, the Custom Audience funtion is introduced. It allows the busniess owner to have an idea on how the campaign is performing. It builds a database and give a score based on the interaction of the targeting audience on the ad that's posted. Whether the ad video was watched completley, or audience clicked on the ad, etc. Also, with the gathered information, this function can determine the similarity of the audiences, so we can have our main target of audience. The collected data are gathered from the API of the hosting campaign and the busniess website. 

Here's a some of what types of interaction this funtion collect:

| Type of Interaction                   | Type of Interaction                              |
|---------------------------------------|--------------------------------------------------|
| The website visitor                   | Facebook page visitor                            |
| Instagram account                     | Website delivery page visitor                    |
| Website contacts page visitor         | Website menu page                                |
| Website Home page visitor             | Website reservation page and if completed or not |
| Interacted with the Facebook page     | If Facebook page or post saved                   |
| Engaged Facebook page/post            | If Facebook page saved                           |
| Interacted with the Instagram account | If Instagram page or post saved                  |
| Engaged Instagram account/post        | If Instagram ad saved                            |

A complete list of data collected can be found in the `.csv` file [`custom_audience_quality_score.csv`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/custom_audience/custom_audience_quality_score.csv).


## Methodology

For such funtion to be able to perform this task of collecting information on the campaign performance, there are two main scripts are developed:

- [`create_custom_audiences.py`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/custom_audience/create_custom_audiences.py).
- [`choose_custom_audience.py`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/custom_audience/choose_custom_audience.py).


In the `create_custom_audiences.py` there are the funtions that gather the data required to build such overview on the performance of the campaign.

```py

# This funtion collect anyone who give the business website a visit 
## without interaction with any of the website pages.
def create_website_ALL_VISITORS_custom_audience():
    pass

# Within this funtion, the data on what interaction happened 
## between the users and the website's pages, either with just 
### the home page to if the user trying to make a reervation
def create_website_event_custom_audience():
    pass

# In this function a data regards the duration of the watched video is collected,
## wether the posted video ad was watched fully or some of it.
def create_video_custom_audience():
    pass

# This funtion gathering the information on the engagement of the users to the Facebook page,
## whether the users saved the page, the post, or an engagement happened to the post.
def create_facebook_action_custom_audience():
    pass

# This exactly like the funtion before but happen to the Instagram account.
def create_instagram_action_custom_audience():
    pass

# Create a list of similar users parameters (Same country, same city,..etc.)
def create_lookalike_audience():
    pass

# This funtion gather all the collected information to have it in one place, 
# either it's from the Website, the Facebook page, or Instagram account
def create_all_custom_audience():
    pass
```

The second step comes the [`choose_custom_audience.py`](https://github.com/AiGotsrl/MS-DSMarketing/blob/develop/src/marketing/custom_audience/choose_custom_audience.py) where it looks into the data were collected and give it score depending on the interaction.


**In a conclusion**, it's a useful builtin funtion to get an overview on how the performance of you campaign affecting the gross of the business and to have an idea on what types of adience are engaged more to our business, so we can focus more on them.

