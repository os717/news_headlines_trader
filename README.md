# news_headlines_trader

This is my submission for a Kaggle competition I entered a while back sponsered by Two Sigma. The aim of the competition was to predit stock movements using the news. 

## Overview

To do this, compeititors were given two training data sets dating from 2007 to 2018:

`Market Data (2007 to 2018) - Provided by Intrinio, containing financial market information such as opening price, closing price, trading volume, calculated returns, etc.`

`News Data (2007 to Present) - Provided by Reuters, containing information about news articles/alerts published about assets, such as article details, sentiment, and other commentary.`

The market data contains a variety of returns calculated over different timespans. All of the return features in this set of market data have these properties:

	* Returns are always calculated either open-to-open (from the opening time of one trading day to the open of another) or close-to-close (from the closing time of one trading day to the open of another).
	* Returns are either raw, meaning that the data is not adjusted against any benchmark, or market-residualized (Mktres), meaning that the movement of the market as a whole has been accounted for, leaving only movements inherent to the instrument.
 
In this competition, you must predict a signed confidence value, (-1, 1), which is multiplied by the market-adjusted return of a given assetCode over a ten day window.


## How I did it:

Thw first step was to find a way to draw out the meaning from news headline segments. After learning of sentiment analysis, I found a Github repositary which uses "sense away neurel networks that use context embedding vectors". Yes, I have no idea what that means but hopefully I will soon :) Here is a link to it:

`https://github.com/explosion/sense2vec`



