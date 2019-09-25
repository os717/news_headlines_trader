import os
import json
import time
import math
import pandas as pd
import matplotlib.pyplot as plt
from src.data_processor import DataLoader
# from src.model import Model
from sklearn.metrics import roc_curve, roc_auc_score
from sklearn.preprocessing import StandardScaler
import matplotlib as mpl
import numpy as np

import tensorflow, tensorboard
from keras.callbacks import TensorBoard
from keras.layers import Input, Dense, Activation, Dropout, LSTM
from keras.models import Model
from keras.optimizers import Adam

def plot_results(predicted_data, true_data):
    fig = plt.figure(facecolor='white')
    ax = fig.add_subplot(111)
    ax.plot(true_data, label='True Data')
    plt.plot(predicted_data, label='Prediction')
    plt.legend()
    plt.show()


def plot_results_multiple(predicted_data, true_data, prediction_len):
    fig = plt.figure(facecolor='white')
    ax = fig.add_subplot(111)
    ax.plot(true_data, label='True Data')
    # Pad the list of predictions to shift it in the graph to it's correct start
    for i, data in enumerate(predicted_data):
        padding = [None for p in range(i * prediction_len)]
        plt.plot(padding + data, label='Prediction')
        plt.legend()
    plt.show()

def plot_roc(probs, y_test,ax):
    fpr, tpr, thresholds = roc_curve(y_test,probs)
    auc_score = round(roc_auc_score(y_test, probs),4)
    ax.plot(fpr, tpr, label=f'Initial LSTM = {auc_score} AUC')
    ax.plot([0, 1], [0, 1], linestyle='--', lw=2, color='k',
         label='Luck')
    ax.set_xlabel("False Positive Rate (1-Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity, Recall)")
    ax.set_title("ROC/AUC: AAPL - Trained AAPL Only - 5day sequence_length")
    ax.legend()

def build_model():
    neurons = 300
    n_steps = 5
    n_features = 24

    #real input is n_iterations, n_timesteps, n_features
    #cat input is n_iterations, n_timesteps, 1

    real_input = Input(shape=(n_steps, n_features,))
    rnn = LSTM(neurons, input_shape=(n_steps, n_features),return_sequences=True)(real_input)
    drop = Dropout(.2)(rnn)
    rnn = LSTM(neurons, input_shape=(n_steps, n_features),return_sequences=True)(drop)
    rnn = LSTM(neurons, input_shape=(n_steps, n_features),return_sequences=False)(rnn)
    drop = Dropout(.2)(rnn)
    dense = Dense(neurons, activation='relu')(drop)
    dense = Dense(1, activation='sigmoid')(dense)
    M = Model(inputs=[real_input], outputs=[dense])
    adam = Adam(lr=0.0005)
    M.compile(loss='binary_crossentropy', optimizer=adam, metrics=['accuracy'])
    return M

def get_test_windows(data_test, testcols, assetNames, seq_len, normalize):
    x_test = []
    y_test = []
    for asset in assetNames:
        window = data_test.loc[data_test.assetName==asset, testcols].tail().values
        window = np.array(window).astype(float)
        if window.shape[0] < seq_len:
            pad = np.zeros((seq_len-window.shape[0],len(testcols)))
            window = np.vstack((pad,window))
        x_test.append(window[:,1:])
        y_test.append(window[-1,0])
    x_test = np.array(x_test).astype(float)
    y_test = np.where(np.array(y_test).astype(float)>0,1,0)
    x_test = normalize_windows(x_test, single_window=False) if normalize else x_test
    return np.array(x_test), np.array(y_test)

def normalize_windows(window_data, single_window=False):
    '''normalize window with a base value of zero'''
    normalized_data = []
    window_data = [window_data] if single_window else window_data
    for window in window_data:
        scaler = StandardScaler()
        normalized_window = scaler.fit_transform(window)
        normalized_data.append(normalized_window)
    return np.array(normalized_data)


if __name__ == '__main__':

    df = pd.read_pickle('../data/init_train_data.pkl')

    test_cols = ["returnsOpenNextMktres10","returnsClosePrevRaw1",
           "returnsOpenPrevRaw1", "returnsClosePrevMktres1",
           "returnsOpenPrevMktres1",
           "returnsClosePrevMktres10",
           "returnsOpenPrevMktres10", "dailychange",
           "dailyaverage","companyCount", "relevance",
           "sentimentNegative", "sentimentNeutral", "sentimentPositive",
           "noveltyCount12H", "noveltyCount24H", "noveltyCount3D",
           "noveltyCount5D", "noveltyCount7D", "volumeCounts12H",
           "volumeCounts24H", "volumeCounts3D", "volumeCounts5D",
           "volumeCounts7D", "coverage"
        ]

    dflate = df.loc[((df.time<20160601) & (df.time>20160501))]

    xall, yall = get_test_windows(dflate, test_cols, dflate.assetName.unique(),5,normalize=True)

    configs = json.load(open('config.json', 'r'))
    # if not os.path.exists(configs['model']['save_dir']): os.makedirs(configs['model']['save_dir'])

    data = DataLoader(
        os.path.join('data', configs['data']['filename']),
        configs['data']['train_test_split'],
        configs['data']['columns']
    )



    # #Get Embedded X,y for each company
    # #Configs
    config_aapl = json.load(open('config_aapl.json', 'r'))
    config_advance = json.load(open('config_advance.json', 'r'))
    config_allstate = json.load(open('config_allstate.json', 'r'))

    data_aapl = DataLoader(
    os.path.join('data', config_aapl['data']['filename']),
    config_aapl['data']['train_test_split'],
    config_aapl['data']['columns']
    )

    data_adv = DataLoader(
    os.path.join('data', config_advance['data']['filename']),
    config_advance['data']['train_test_split'],
    config_advance['data']['columns']
    )

    data_alls = DataLoader(
    os.path.join('data', config_allstate['data']['filename']),
    config_allstate['data']['train_test_split'],
    config_allstate['data']['columns']
    )
    #AAPL Data
    xapl, yapl = data_aapl.get_train_data(
        seq_len=config_aapl['data']['sequence_length'],
        normalize=config_aapl['data']['normalize']
    )

    Xapl = [xapl,np.zeros((xapl.shape[0],xapl.shape[1],1))]

    #Advance Data
    xadv, yadv = data_adv.get_train_data(
        seq_len=config_advance['data']['sequence_length'],
        normalize=config_advance['data']['normalize']
    )

    Xadv = [xadv,np.ones((xadv.shape[0],xadv.shape[1],1))]

    #Allstate Data
    xalls, yalls = data_alls.get_train_data(
        seq_len=config_allstate['data']['sequence_length'],
        normalize=config_allstate['data']['normalize']
    )
    allemb = np.ones((xalls.shape[0],xalls.shape[1],1))+1
    Xalls = [xadv,allemb]

    # #Test With Embedding
    # #AAPL
    x_test_apl, y_test_apl = data_aapl.get_test_data(
        seq_len=config_aapl['data']['sequence_length'],
        normalize=config_aapl['data']['normalize']
    )
    em_apl = np.zeros((x_test_apl.shape[0], x_test_apl.shape[1],1))
    X_test_apl = [x_test_apl, em_apl]

    #Advance
    x_test_adv, y_test_adv = data_adv.get_test_data(
        seq_len=config_advance['data']['sequence_length'],
        normalize=config_advance['data']['normalize']
    )
    em_adv = np.ones((x_test_adv.shape[0], x_test_adv.shape[1],1))
    X_test_adv = [x_test_adv, em_adv]

    # #Allstate
    x_test_alls, y_test_alls = data_alls.get_test_data(
        seq_len=config_allstate['data']['sequence_length'],
        normalize=config_allstate['data']['normalize']
    )
    em_alls = np.ones((x_test_alls.shape[0], x_test_alls.shape[1],1)) + 1
    X_test_alls = [x_test_alls, em_alls]

 
    #Build Model for Embedding
    tbCallBack = TensorBoard(log_dir='./logs', histogram_freq=0, write_graph=True, write_images=True)
    model = build_model()

    model.fit(xapl, yapl, epochs=5, batch_size=50, validation_data=[x_test_apl, y_test_apl], callbacks=[tbCallBack])
    # for X,y in zip([Xapl, Xadv, Xalls],[yapl, yadv, yalls]):
    #     model.fit(X,y, 
    #         epochs=config_allstate['training']['epochs'],
    #         batch_size=config_allstate['training']['batch_size'],
    #         validation_data=(X_test_alls, y_test_alls))


    ##NO EMBED
    # # out-of memory generative training
    # data = DataLoader(
    # os.path.join('data', configs['data']['filename']),
    # configs['data']['train_test_split'],
    # configs['data']['columns']
    # )
    # model = Model()
    # model.build_model(configs)
    # steps_per_epoch = math.ceil((data.len_train - configs['data']['sequence_length']) / configs['training']['batch_size'])
    # model.train_generator(
    #     data_gen=data.generate_train_batch(
    #         seq_len=configs['data']['sequence_length'],
    #         batch_size=configs['training']['batch_size'],
    #         normalize=configs['data']['normalize']
    #     ),
    #     epochs=configs['training']['epochs'],
    #     batch_size=configs['training']['batch_size'],
    #     steps_per_epoch=steps_per_epoch,
    #     save_dir=configs['model']['save_dir']
    # )

    # x_test, y_test = data.get_test_data(
    #     seq_len=configs['data']['sequence_length'],
    #     normalize=configs['data']['normalize']
    # )
    #no embedding
    # predictions = model.predict_point_by_point(x_test)




    predictions = model.predict(xall)
    predictions = np.reshape(predictions, (predictions.size,))

    fig, ax = plt.subplots(figsize=(12,12))
    plot_roc(predictions, yall, ax)
    plt.title('ROC/AUC on Final LSTM, All Companies, 06/01/2016')
    plt.show()