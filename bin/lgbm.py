from core.data_processor import DataPrepper
from datetime import datetime, timedelta
import numpy as np 
import pandas as pd 
from pandas.api.types import is_numeric_dtype
import matplotlib as plt 
from plot_helpers.classifier_performance_plothelper import plot_coefficient_importances
from plot_helpers.model_plots import plot_confusion_matrix, plot_roc
from plot_helpers.tree_plothelper import *
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split as sk_train_test_split
from lightgbm import LGBMClassifier
import joblib

from multiprocessing import Pool

from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import log_loss
from sklearn.decomposition import PCA 

from skopt import gp_minimize
from skopt.plots import plot_convergence
import gc


from core.evaluator import ReturnsEvaluator

class Featurizer():
    def __init__(self, assetId='assetCode',
                       n_lag=[3,7,14,],
                       shift_size=1, 
                       return_features=['returnsClosePrevMktres10','returnsClosePrevRaw10',
                                        'returnsOpenPrevMktres1', 'returnsOpenPrevRaw1',
                                        'open','close']
                ):
        self.assetId = assetId
        self.n_lag = n_lag
        self.shift_size = shift_size
        self.return_features = return_features

    def transform(self, df):
        new_df = self.generate_lag_features(df)
        df = pd.merge(df, new_df, how='left', on=['time', self.assetId])
        df = self.mis_impute(df)
        df.dropna(axis=0, inplace=True)
        return df


    def create_lag(self, df_code):
        # code = df_code.loc[:,self.assetId].unique()
        for col in self.return_features:
            for window in self.n_lag:
                rolled = df_code[col].shift(self.shift_size).rolling(window=window)
                lag_mean = rolled.mean()
                lag_max = rolled.max()
                lag_min = rolled.min()
                lag_std = rolled.std()
                df_code['%s_lag_%s_mean'%(col,window)] = lag_mean
                df_code['%s_lag_%s_max'%(col,window)] = lag_max
                df_code['%s_lag_%s_min'%(col,window)] = lag_min
                # df_code['%s_lag_%s_std'%(col,window)] = lag_std
        return df_code.fillna(-1)

    def generate_lag_features(self,df):
        features = ['time', self.assetId, 'volume', 'close', 'open',
       'returnsClosePrevRaw1', 'returnsOpenPrevRaw1',
       'returnsClosePrevMktres1', 'returnsOpenPrevMktres1',
       'returnsClosePrevRaw10', 'returnsOpenPrevRaw10',
       'returnsClosePrevMktres10', 'returnsOpenPrevMktres10',
       'returnsOpenNextMktres10', 'universe']
        df = df.loc[:,features]
    
        assetCodes = df[self.assetId].unique()
        df_codes = df.groupby(self.assetId)
        df_codes = [df_code[1][['time', self.assetId]+self.return_features] for df_code in df_codes]
        pool = Pool(4)
        all_df = pool.map(self.create_lag, df_codes)
        new_df = pd.concat(all_df)  
        new_df.drop(self.return_features,axis=1,inplace=True)
        pool.close()

        return new_df

    def mis_impute(self, df):
        for i in df.columns:
            if df[i].dtype == "object":
                df[i] = df[i].fillna("other")
            elif (df[i].dtype == "int64" or df[i].dtype == "float64"):
                df[i] = df[i].fillna(df[i].mean())
            else:
                pass
        return df

class Mixturizer():
    def __init__(self):
        self.scaler = StandardScaler()
        self.mixture = GaussianMixture(3, random_state=42)

    def fit(self, df, mixturecols):
        X = df.loc[:,mixturecols]
        self.scaler.fit(X)
        X = np.nan_to_num(self.scaler.transform(X))
        self.mixture.fit(X)

    def transform(self, df, mixturecols):
        X = df.loc[:,mixturecols]
        X = np.nan_to_num(self.scaler.transform(X))
        features = self.mixture.predict_proba(X)
        features = pd.DataFrame(features, columns=['mixture1', 'mixture2', 'mixture3'])
        return df.join(features)

class PCAFeaturizer():
    def __init__(self):
        self.cols = ['volume', 'close', 'open',
       'returnsClosePrevRaw1', 'returnsOpenPrevRaw1',
       'returnsClosePrevMktres1', 'returnsOpenPrevMktres1',
       'returnsClosePrevRaw10', 'returnsOpenPrevRaw10',
       'returnsClosePrevMktres10', 'returnsOpenPrevMktres10', 'dailychange',
       'todayreturnraw', 'pricevolume',
       'returnsClosePrevMktres10_lag_3_mean',
       'returnsClosePrevMktres10_lag_3_max',
       'returnsClosePrevMktres10_lag_3_min',
       'returnsClosePrevMktres10_lag_7_mean',
       'returnsClosePrevMktres10_lag_7_max',
       'returnsClosePrevMktres10_lag_7_min',
       'returnsClosePrevMktres10_lag_14_mean',
       'returnsClosePrevMktres10_lag_14_max',
       'returnsClosePrevMktres10_lag_14_min',
       'returnsOpenPrevMktres1_lag_3_mean',
       'returnsOpenPrevMktres1_lag_3_max',
       'returnsOpenPrevMktres1_lag_3_min',
       'returnsOpenPrevMktres1_lag_7_mean',
       'returnsOpenPrevMktres1_lag_7_max',
       'returnsOpenPrevMktres1_lag_7_min',
       'returnsOpenPrevMktres1_lag_14_mean',
       'returnsOpenPrevMktres1_lag_14_max',
       'returnsOpenPrevMktres1_lag_14_min']
        self.pca = PCA()
        self.standardscaler = StandardScaler()
        self.minmax = MinMaxScaler(feature_range=(0.0001,1.0001))


    def fit(self, X):
        self.standardscaler.fit(X.loc[:,self.cols])
        X = self.standardscaler.transform(X.loc[:,self.cols])
        self.pca.fit(X)

    def transform(self, X, num_components=3):
        df = X.copy()
        components = self.standardscaler.transform(X.loc[:,self.cols]) 
        components = self.pca.fit_transform(components)[:,:num_components]
        components = self.minmax.fit_transform(components)
        components = np.log(components)
        for i in range(num_components):
            df[f'PCA_{i}'] = components[:,i]

        return df


class BayesianOptimizerLGBM():
    def __init__(self,spaces):
        self.spaces = spaces

    def fit(self, X_train, y_train, X_val, y_val):
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val 
        self.res = gp_minimize(self._optimize, self.spaces, acq_func="EI",n_calls=20)

    def _optimize(self, x):

        gbm = LGBMClassifier(
                            boosting_type='dart',
                            learning_rate=x[0],
                            num_leaves=x[1],
                            min_data_in_leaf=x[2],
                            num_iteration=x[3],
                            max_bin=x[4],
                            verbose=1, 
                            n_jobs=-1)
        gbm.fit(self.X_train, self.y_train, eval_set=(self.X_val, self.y_val),
                eval_metric=['binary_logloss'], verbose=True, early_stopping_rounds=5)
        y_pred = gbm.predict_proba(self.X_val)
        score = log_loss(self.y_val, y_pred)
        print("score" , score)
        return score


def reduce_mem_usage(df):
    """ iterate through all the columns of a dataframe and modify the data type
        to reduce memory usage.        
    """
    start_mem = df.memory_usage().sum() / 1024**2
    print('Memory usage of dataframe is {:.2f} MB'.format(start_mem))

    for col in df.columns:
        col_type = df[col].dtype

        if is_numeric_dtype(col_type):
            col_type = col_type.name
            
            c_min = df[col].min()
            c_max = df[col].max()
            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                elif c_min > np.iinfo(np.int64).min and c_max < np.iinfo(np.int64).max:
                    df[col] = df[col].astype(np.int64)  
            else:
                if c_min > np.finfo(np.float16).min and c_max < np.finfo(np.float16).max:
                    df[col] = df[col].astype(np.float32)
                elif c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)

    end_mem = df.memory_usage().sum() / 1024**2
    print('Memory usage after optimization is: {:.2f} MB'.format(end_mem))
    print('Decreased by {:.1f}%'.format(100 * (start_mem - end_mem) / start_mem))
    return df


if __name__ == '__main__':
    # data = DataPrepper()
    # df = pd.read_pickle('../data/original_merged_train.pkl')
    # df = df.loc[df.time>=20100101]
    # y = np.where(df.pop('returnsOpenNextMktres10').values>0, 1, 0).astype(int)
    # X = df
    # drop_cols = ['assetCode','assetName','marketCommentary', 'time']
    # X_features = [c for c in X.columns.values if c not in drop_cols]
    # X = X.loc[:,X_features]
    
    # X_train, X_val, y_train, y_val = sk_train_test_split(X, y, random_state=0)


    # print("len X_Train before features", len(X_train))
    # print("len y_Train before features", len(y_train))


    # #Make new features
    # featurizer = Featurizer()
    # X_train = featurizer.transform(X_train)
    # X_val = featurizer.transform(X_val)
    # X_train.drop(columns=['assetCode','assetName', 'time'], inplace=True)
    # X_val.drop(columns=['assetCode', 'assetName', 'time'], inplace=True)
    # print("len X_Train after features", len(X_train))
    # print("len y_Train after features", len(y_train))
    # X_train.to_pickle('../data/lag_features/X_train_rand.pkl')
    # X_val.to_pickle('../data/lag_features/X_val_rand.pkl')
    # np.save('../data/lag_features/y_train_rand.pkl', y_train)
    # np.save('../data/lag_features/y_val_rand.pkl', y_val)

    X = pd.read_pickle('../data/lag_features/X_all_features.pkl')
    y = np.load('../data/lag_features/y_all_features.npy')
    drop_cols = ['assetCode','assetName','marketCommentary', 'time']
    X_features = [c for c in X.columns.values if c not in drop_cols]

    data = DataPrepper()
    X_train, X_val, y_train, y_val = data.train_test_split(X,y)

    drop_cols = ['assetCode','assetName','marketCommentary', 'time']

    X_train = X_train.loc[:,X_features]
    X_val = X_val.loc[:, X_features]


    #Mixture Modeling
    # mixture = Mixturizer()
    # mixturecols = ['returnsOpenPrevMktr es10', 'returnsOpenPrevMktres1']
    # mixture.fit(X_train, mixturecols)
    # X_train = mixture.transform(X_train, mixturecols)
    # X_val = mixture.transform(X_val, mixturecols)


    #PCA Featurizing
    # pca = PCAFeaturizer()
    # pca.fit(X_train)
    # X_train = pca.transform(X_train)
    # X_val = pca.transform(X_val)

    # optimize GBM
    # spaces = [
    # (0.05, 0.15), #learning_rate
    # (100, 2000), #num_leaves
    # (200, 400),#min_data_in_leaf,
    # (300, 300),  #num_iterations
    # (200, 400) #max_bin
    # ]

    # opt = BayesianOptimizerLGBM(spaces)
    # opt.fit(X_train, y_train, X_val, y_val)
    # print("optimal params", opt.res.x)
    # plot_convergence(opt.res)
    # plt.show()
    # x = opt.res
    x = [0.12178047793601021, 1189, 395, 313, 399] #time series
    # x = [0.10192437737356348, 1011, 399, 319, 242]
    # x_dart = [0.14975024553335256, 279, 388, 394]

    gbm = LGBMClassifier(boosting_type='gbdt',
                            learning_rate=x[0],
                            num_leaves=x[1],
                            min_data_in_leaf=x[2],
                            num_iteration=x[3],
                            max_bin=x[4],
                            verbose=1, 
                            n_jobs=-1)

    gbm.fit(X_train, y_train, eval_set=(X_val, y_val),
                eval_metric=['binary_logloss'], verbose=True, early_stopping_rounds=5)


    fig, ax = plt.subplots(figsize=(12,8))
    plot_roc(gbm, X_val, y_val, ax, 'GBM2 with Tuning and Feature Engineering')
    plt.show()
    
    
       
    # del X_train
    # del X_val
    # del y_train
    # del y_val
    # gc.collect()


    # X_test = pd.read_pickle('../data/test_data.pkl')
    # X_test = reduce_mem_usage(X_test)
    # X_test = featurizer.transform(X_test)
    # X_test.to_pickle('../data/X_test_featurized.pkl')
    # preds = gbm.predict_proba(X_test.loc[:, X_features])

    # minmax = MinMaxScaler()

    # preds = minmax.fit_transform(preds)[:,1]

    # preds = preds*2-1

    # X_test['confidenceValue'] = preds

    # evaluator = ReturnsEvaluator() 

    # print(evaluator.get_kaggle_mean_variance(X_test))








