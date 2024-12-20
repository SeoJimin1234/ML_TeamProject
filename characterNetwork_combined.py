# -*- coding: utf-8 -*-
"""
Created on Tues Oct 16 23:33:04 2018

@author: Ken Huang
"""

import codecs
import os
import spacy
import json
import pandas as pd
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
from afinn import Afinn
from nltk.tokenize import sent_tokenize
from sklearn.feature_extraction.text import CountVectorizer
from collections import Counter

def flatten(input_list):
    '''
    A function to flatten complex list.
    :param input_list: The list to be flatten
    :return: the flattened list.
    '''

    flat_list = []
    for i in input_list:
        if type(i) == list:
            flat_list += flatten(i)
        else:
            flat_list += [i]

    return flat_list


def common_words(path):
    '''
    A function to read-in the top common words from external .txt document.
    :param path: The path where the common words info is stored.
    :return: A set of the top common words.
    '''

    with codecs.open(path) as f:
        words = f.read()
        words = json.loads(words)

    return set(words)


def read_novel(book_name, path):
    '''
    A function to read-in the novel text from given path.
    :param book_name: The name of the novel.
    :param path: The path where the novel text file is stored.
    :return: the novel text.
    '''

    book_list = os.listdir(path)
    book_list = [i for i in book_list if i.find(book_name) >= 0]
    novel = ''
    for i in book_list:
        with codecs.open(path / i, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read().replace('\r', ' ').replace('\n', ' ').replace("\'", "'")
        novel += ' ' + data

    return novel


def name_entity_recognition(sentence):
    '''
    A function to retrieve name entities in a sentence.
    :param sentence: the sentence to retrieve names from.
    :return: a name entity list of the sentence.
    '''

    doc = nlp(sentence)
    # retrieve person and organization's name from the sentence
    name_entity = [x for x in doc.ents if x.label_ in ['PERSON', 'ORG']]
    # convert all names to lowercase and remove 's in names
    name_entity = [str(x).lower().replace("'s","") for x in name_entity]
    # split names into single words ('Harry Potter' -> ['Harry', 'Potter'])
    name_entity = [x.split(' ') for x in name_entity]
    # flatten the name list
    name_entity = flatten(name_entity)
    # remove name words that are less than 3 letters to raise recognition accuracy
    name_entity = [x for x in name_entity if len(x) >= 3]
    # remove name words that are in the set of 4000 common words
    name_entity = [x for x in name_entity if x not in words]

    return name_entity


def iterative_NER(sentence_list, threshold_rate=0.0005):
    '''
    A function to execute the name entity recognition function iteratively. The purpose of this
    function is to recognise all the important names while reducing recognition errors.
    :param sentence_list: the list of sentences from the novel
    :param threshold_rate: the per sentence frequency threshold, if a word's frequency is lower than this
    threshold, it would be removed from the list because there might be recognition errors.
    :return: a non-duplicate list of names in the novel.
    '''

    output = []
    for i in sentence_list:
        name_list = name_entity_recognition(i)
        if name_list != []:
            output.append(name_list)
    output = flatten(output)
    from collections import Counter
    output = Counter(output)
    output = [x for x in output if output[x] >= threshold_rate * len(sentence_list)]

    return output


def top_names(name_list, novel, top_num=20):
    '''
    A function to return the top names in a novel and their frequencies.
    :param name_list: the non-duplicate list of names of a novel.
    :param novel: the novel text.
    :param top_num: the number of names the function finally output.
    :return: the list of top names and the list of top names' frequency.
    '''

    vect = CountVectorizer(vocabulary=name_list, stop_words='english')
    name_frequency = vect.fit_transform([novel.lower()])
    name_frequency = pd.DataFrame(name_frequency.toarray(), columns=vect.get_feature_names_out())
    name_frequency = name_frequency.T
    name_frequency = name_frequency.sort_values(by=0, ascending=False)
    name_frequency = name_frequency[0:top_num]
    names = list(name_frequency.index)
    name_frequency = list(name_frequency[0])

    return name_frequency, names


def calculate_align_rate(sentence_list):
    '''
    Function to calculate the align_rate of the whole novel
    :param sentence_list: the list of sentence of the whole novel.
    :return: the align rate of the novel.
    '''
    afinn = Afinn()
    sentiment_score = [afinn.score(x) for x in sentence_list]
    align_rate = np.sum(sentiment_score)/len(np.nonzero(sentiment_score)[0]) * -2

    return align_rate


def calculate_matrix(name_list, sentence_list, align_rate):
    '''
    Function to calculate the co-occurrence matrix and sentiment matrix among all the top characters
    :param name_list: the list of names of the top characters in the novel.
    :param sentence_list: the list of sentences in the novel.
    :param align_rate: the sentiment alignment rate to align the sentiment score between characters due to the writing style of
    the author. Every co-occurrence will lead to an increase or decrease of one unit of align_rate.
    :return: the co-occurrence matrix and sentiment matrix.
    '''

    # calculate a sentiment score for each sentence in the novel
    afinn = Afinn()
    sentiment_score = [afinn.score(x) for x in sentence_list]
    # calculate occurrence matrix and sentiment matrix among the top characters
    name_vect = CountVectorizer(vocabulary=name_list, binary=True)
    occurrence_each_sentence = name_vect.fit_transform(sentence_list).toarray()
    cooccurrence_matrix = np.dot(occurrence_each_sentence.T, occurrence_each_sentence)
    sentiment_matrix = np.dot(occurrence_each_sentence.T, (occurrence_each_sentence.T * sentiment_score).T)
    sentiment_matrix += align_rate * cooccurrence_matrix
    cooccurrence_matrix = np.tril(cooccurrence_matrix)
    sentiment_matrix = np.tril(sentiment_matrix)
    # diagonals of the matrices are set to be 0 (co-occurrence of name itself is meaningless)
    shape = cooccurrence_matrix.shape[0]
    cooccurrence_matrix[[range(shape)], [range(shape)]] = 0
    sentiment_matrix[[range(shape)], [range(shape)]] = 0

    return cooccurrence_matrix, sentiment_matrix

def combine_edgelists(co_occurrence_file, sentiment_file, output_file):
    '''
    Combine co-occurrence and sentiment edgelists into a single file.
    :param co_occurrence_file: Path to the co-occurrence edgelist file.
    :param sentiment_file: Path to the sentiment edgelist file.
    :param output_file: Path to save the combined edgelist file.
    '''
    # Load the two edgelists
    co_occurrence_edges = nx.read_edgelist(co_occurrence_file, data=True)
    sentiment_edges = nx.read_edgelist(sentiment_file, data=True)

    # Create a new graph for the combined edgelist
    combined_graph = nx.Graph()

    # Add co-occurrence edges
    for u, v, data in co_occurrence_edges.edges(data=True):
        combined_graph.add_edge(u, v, co_occurence=data['co_occurence'], sentiment=0)  # Initialize sentiment as 0

    # Add sentiment edges
    for u, v, data in sentiment_edges.edges(data=True):
        if combined_graph.has_edge(u, v):
            combined_graph[u][v]['sentiment'] = data['sentiment']  # Update sentiment if edge exists
        else:
            combined_graph.add_edge(u, v, co_occurence=0, sentiment=data['weight'])  # Initialize co-occurrence as 0

    # Save the combined edgelist
    nx.write_edgelist(combined_graph, output_file, data=True)

def matrix_to_combined_edge_list(cooccurrence_matrix, sentiment_matrix, name_list):
    '''
    Function to create a combined edge list from co-occurrence and sentiment matrices.
    :param cooccurrence_matrix: Co-occurrence matrix.
    :param sentiment_matrix: Sentiment matrix.
    :param name_list: The list of names of the top characters in the novel.
    :return: A combined edge list with 'co_occurrence' and 'sentiment' weights.
    '''
    edge_list = []
    shape = cooccurrence_matrix.shape[0]
    lower_tri_loc = list(zip(*np.where(np.triu(np.ones([shape, shape])) == 0)))

    # Normalize matrices
    normalized_cooccurrence = cooccurrence_matrix / np.max(cooccurrence_matrix)
    normalized_sentiment = sentiment_matrix / np.max(np.abs(sentiment_matrix))

    for i in lower_tri_loc:
        if cooccurrence_matrix[i[0], i[1]] != 0 or sentiment_matrix[i[0], i[1]] != 0:
            edge_list.append((
                name_list[i[0]],
                name_list[i[1]],
                {
                    'co_occurrence': np.log(2000 * normalized_cooccurrence[i] + 1) * 0.7 if cooccurrence_matrix[i[0], i[1]] != 0 else 0,
                    'sentiment': np.log(np.abs(1000 * normalized_sentiment[i]) + 1) * 0.7 if sentiment_matrix[i[0], i[1]] != 0 else 0
                }
            ))

    return edge_list


def plot_combined_graph(name_list, name_frequency, cooccurrence_matrix, sentiment_matrix, plt_name, path=''):
    '''
    Function to create and save a combined network graph (with co-occurrence and sentiment).
    :param name_list: The list of top character names in the novel.
    :param name_frequency: The list containing the frequencies of the top names.
    :param cooccurrence_matrix: Co-occurrence matrix.
    :param sentiment_matrix: Sentiment matrix.
    :param plt_name: The name of the plot and edgelist file to output.
    :param path: The path to output the files.
    '''
    label = {i: i for i in name_list}
    edge_list = matrix_to_combined_edge_list(cooccurrence_matrix, sentiment_matrix, name_list)
    normalized_frequency = np.array(name_frequency) / np.max(name_frequency)

    G = nx.Graph()
    G.add_nodes_from(name_list)
    G.add_edges_from(edge_list)
    pos = nx.circular_layout(G)
    edges = G.edges()

    # Extract weights for plotting
    co_occurrence_weights = [G[u][v]['co_occurrence'] for u, v in edges]
    sentiment_weights = [G[u][v]['sentiment'] for u, v in edges]

    # Plot the combined graph
    plt.figure(figsize=(20, 20))
    nx.draw(
        G, pos, node_color='#A0CBE2',
        node_size=np.sqrt(normalized_frequency) * 4000,
        linewidths=10, font_size=35, labels=label,
        edge_color=sentiment_weights, edge_cmap=plt.cm.RdYlBu,
        with_labels=True, width=co_occurrence_weights
    )

    # Save the plot and the combined edgelist
    plt.savefig(path + plt_name + '.png')
    nx.write_edgelist(G, path + plt_name + '.edgelist', data=True)

def classify_gender_with_kaggle_and_context(name_list, gender_data, sentence_list):
    '''
    Function to classify gender based on names using the Kaggle dataset and refine predictions using context.
    :param name_list: List of names to classify.
    :param gender_data: DataFrame containing name and gender mappings.
    :param sentence_list: List of sentences from the text for context-based analysis.
    :return: Dictionary mapping names to genders.
    '''
    gender_dict = {}

    for name in name_list:
        first_name = name.split()[0].lower()
        gender_row = gender_data[gender_data['Name'] == first_name]

        # Use Kaggle dataset for gender prediction
        if not gender_row.empty:
            gender_dict[name] = gender_row.iloc[0]['Gender']
        else:
            # Use context to refine predictions
            context_sentences = [sent for sent in sentence_list if name in sent.lower()]
            pronoun_counter = Counter()

            for sentence in context_sentences:
                # Count gender-specific pronouns
                pronoun_counter['Male'] += sentence.lower().count('he') + sentence.lower().count('him')
                pronoun_counter['Female'] += sentence.lower().count('she') + sentence.lower().count('her')

            # Refine gender prediction based on pronouns
            if pronoun_counter['Male'] > pronoun_counter['Female']:
                gender_dict[name] = 'M'
            elif pronoun_counter['Female'] > pronoun_counter['Male']:
                gender_dict[name] = 'F'
            else:
                # Default to male if no clear context
                gender_dict[name] = 'N'
                

    return gender_dict


if __name__ == '__main__':
    nlp = spacy.load('en_core_web_sm')
    nlp.max_length = 2000000 
    words = common_words('common_datas/common_words.txt')
    novel_name = 'ThePhantomOfTheOpera'
    novel_folder = Path(os.getcwd()) / 'novels'
    novel = read_novel(novel_name, novel_folder)
    sentence_list = sent_tokenize(novel)
    # sentence_list = [sent.text for sent in nlp(novel).sents]
    align_rate = calculate_align_rate(sentence_list)
    preliminary_name_list = iterative_NER(sentence_list)
    print("!!!!!! 등장인물 이름: ", preliminary_name_list)
    name_frequency, name_list = top_names(preliminary_name_list, novel, 25)
    
    # 성별 예측
    gender_data = pd.read_csv('common_datas/gender_by_name.csv')
    gender_data['Name'] = gender_data['Name'].str.lower()  # 이름을 소문자로 통일
    
    predicted_genders = classify_gender_with_kaggle_and_context(name_list, gender_data, sentence_list)
    print("\n!!!!!! 성별 예측 결과:", predicted_genders)
    
    nodelist_path = f'./graphs/{novel_name} gender.nodelist'
    with open(nodelist_path, 'w', encoding='utf-8') as f:
        for name, gender in predicted_genders.items():
            f.write(f"{name},{gender}\n")

    cooccurrence_matrix, sentiment_matrix = calculate_matrix(name_list, sentence_list, align_rate)

    # Create and save the combined graph
    plot_combined_graph(
        name_list,
        name_frequency,
        cooccurrence_matrix,
        sentiment_matrix,
        novel_name + ' combined graph',
        path='./graphs/'
    )
