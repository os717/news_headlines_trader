# news_headlines_trader

This is my submission for a Kaggle competition I entered a while back sponsered by Two Sigma. The aim of the competition was to predit stock movements using the news. 

## Overview

To do this, compeititors were given two training data sets dating from 2007 to 2018:

`Market Data (2007 to 2016) - Provided by Intrinio, containing financial market information such as opening price, closing price, trading volume, calculated returns, etc.`

`News Data (2007 to 2016) - Provided by Reuters, containing information about news articles/alerts published about assets, such as article details, sentiment, and other commentary.`

The market data contains a variety of returns calculated over different timespans. All of the return features in this set of market data have these properties:

	* Returns are always calculated either open-to-open (from the opening time of one trading day to the open of another) or close-to-close (from the closing time of one trading day to the open of another).
	* Returns are either raw, meaning that the data is not adjusted against any benchmark, or market-residualized (Mktres), meaning that the movement of the market as a whole has been accounted for, leaving only movements inherent to the instrument.
 
In this competition, you must predict a signed confidence value, (-1, 1), which is multiplied by the market-adjusted return of a given assetCode over a ten day window.


## How I did it:

The first step was to find a way to draw out the meaning from news headline segments. After learning of sentiment analysis, I found a Github repositary which uses "sense away neurel networks that use context embedding vectors". Yes, I have no idea what that means but hopefully I will soon :) Here is a link to it:

`https://github.com/explosion/sense2vec`

The next steps required modelling - and a lot of it! Coming from a Computer Engineering-y background meant that, at the time the competition started, I had no real idea what the best models to use were for every situation. But, after a lot of asking, I eventually created a modelling strategey.

1)  I first applied a baseline ROC for LightGBM (defaultish settings) on the entire holdout set which was good enough to bring my up to the 9th decile. But I needed to find a way to rise further up the ranks by loking for more nuanced trends

2) I then looked to model single companies since clustering yielded no clear groups which had similar enough charachteristics. I applyed a gradient-boosting forrest over Apple stocks and compared that to the ROC and noticed that according to my model the companies most recent reurns were the largest factor effecting its next 10 day return. I tried a logistic regression which showed that the most recent news about Apple most effect my model. Doing this, helped me to bring my model up the live rankings but in order to further propel myself up the leaderboards, I looked to use Long-Short Memory Networks.

3) After a lot, and I mean a lot, of reading about LSTM I found that they are incredibly effective at time-series analysis. To implement this into my model, I based it on a model which can be found here: ` https://github.com/jaungiers/LSTM-Neural-Network-for-Time-Series-Prediction`. This allowed me to add additional layers of compexity to my model which helped me to shoot up the rankings!

## Conclusion

I definately was not good enough to enter this competition when it opened last year. I had only just started university and this competition was open to all university students: undergraduates, masters and post-docs! It started off as a bit of fun on the side and then slowly I started to spend more time on it as the weeks progressed - so much so that I was giving up full weekends just to work on it. I am incredidibly proud of what I have achieved and definately hope to do more financial modelling in the future.

Also I scored in top 30% :p
