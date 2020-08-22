import GetOldTweets3 as got
import datetime, time
import csv
import numpy as np
import statistics
from scipy.stats import ttest_ind


class DateAndTime:
    def __init__(self, delimiter="-"):
        self.current_date_and_time = datetime.datetime.now()
        self.delimiter = delimiter

    def get_current_date_and_time(self):
        return self.current_date_and_time

    def get_current_date(self):
        year = str(self.current_date_and_time.year)
        month = str(self.current_date_and_time.month)
        day = str(self.current_date_and_time.day)

        if len(month) == 1:
            month = "0" + month

        if len(day) == 1:
            day = "0" + day

        current_date = year + self.delimiter + month + self.delimiter + day
        return current_date


# Twitter Database API Build 1.2
class TwitterDatabaseAPI:
    default_begin_date = "2018-01-01"
    default_end_date = DateAndTime().get_current_date()
    default_limit = 10

    def __init__(self, user_file, query_file, begin_date=default_begin_date,
                 end_date=default_end_date, limit=default_limit, debug_mode=False):
        self.user_file = user_file
        self.query_file = query_file
        self.user_name_list = []
        self.text_query_list = []
        self.database = {}
        self.results = []
        self.tweets = []

        self.begin_date = begin_date
        self.end_date = end_date
        self.limit = limit
        self.num_tweets = 0
        self.num_tweets_removed = 0
        self.debug_mode = debug_mode

        self.perform_scrape()

    def get_search_parameters(self):
        with open(self.user_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if len(row) > 0:
                    self.user_name_list.append(row[0])
                    line_count += 1
            if self.debug_mode:
                print(f'Read {line_count} user names.')

        with open(self.query_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                if len(row) > 0:
                    self.text_query_list.append(row[0])
                    line_count += 1
            if self.debug_mode:
                print(f'Read {line_count} text queries.\n')

    def get_user_tweets(self, user_name, text_query):
        tweet_criteria = got.manager.TweetCriteria().setQuerySearch(text_query) \
            .setSince(self.begin_date) \
            .setUntil(self.end_date) \
            .setMaxTweets(self.limit) \
            .setUsername(user_name)
        tweets = got.manager.TweetManager.getTweets(tweet_criteria)
        if self.debug_mode:
            if not tweets:
                print('No tweets were found for username: ' + user_name + ' for text query: ' + text_query)
            else:
                print('Successfully scraped ' + str(len(tweets)) + ' tweet(s)')
                self.num_tweets += len(tweets)
        else:
            self.num_tweets += len(tweets)
        return tweets

    def get_tweets_database(self):
        self.get_search_parameters()
        timeout_limit = 0.075 # 15 minute (900 seconds) / 12,000 tweets
        num_completed_tweet_packets = 0
        num_tweet_packets = len(self.user_name_list) * len(self.text_query_list)

        if self.debug_mode:
            print('-- Process Started --')

        for user_name in self.user_name_list:
            user_query_tweets = [self.text_query_list]
            user_tweets = []
            for query in self.text_query_list:
                tweets = self.get_user_tweets(user_name, query)
                user_tweets.append(tweets)

                timeout = timeout_limit * len(tweets)

                if self.debug_mode:
                    num_completed_tweet_packets += 1
                    completion_percentage = num_completed_tweet_packets/num_tweet_packets
                    print("Twitter Scraping " + str(round(completion_percentage, 3)*100) + "% Completed")
                    print("-- Process Paused For " + str(round(timeout, 3)) + " seconds --\n")

                time.sleep(timeout)

                if self.debug_mode:
                    print("-- Process Resumed --")

            user_query_tweets.append(user_tweets)
            self.database[user_name] = user_query_tweets
        print('-- Process Ended --')
        print(str(self.num_tweets) + " tweets scraped.")

    def translate_database_to_table(self):
        header = ['User Name', 'Query', 'Tweet', 'Tweet Date']
        self.results.append(header)

        for user_name in self.database:
            user_query_tweets = self.database[user_name]
            text_query = user_query_tweets[0]
            user_tweets = user_query_tweets[1]

            for index in range(len(text_query)):
                # Finds tweets for a specific indexed query
                tweets = user_tweets[index]
                for tweet in tweets:
                    # Filters out repeated tweets
                    if tweet.text not in self.tweets:
                        self.tweets.append(tweet.text)
                        self.results.append([user_name, text_query[index], tweet.text, tweet.date])
                    else:
                        self.num_tweets_removed += 1

        print(str(self.num_tweets_removed) + ' Tweets filtered out.')
        print(str(self.num_tweets - self.num_tweets_removed) + ' Tweets scraped total.')

    def perform_scrape(self):
        self.get_tweets_database()
        self.translate_database_to_table()

    def export_to_csv(self, csv_name):
        with open(csv_name, mode='w', encoding='utf-16') as csv_writer:
            writer = csv.writer(csv_writer, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for line in self.results:
                writer.writerow(line)


# LIWC API Build 1.2.1 (Bug Fixes)
class LinguisticInquiryWordCountAPI:

    def __init__(self):
        self.dictionary_file = 'Dictionaries/Default.dic'
        self.conditions = {}
        self.terms = {}

        self.undesired_list = []
        self.undesired_list_file = []

        self.target_file = 'None'
        self.target_type = '.txt'
        self.target_array = []

        self.input_target_columns = []
        self.target_columns = []
        self.word_count_columns = []
        self.analysis_columns = []
        self.results = []

        self.number_representation = 'Default'

    # Dictionary Handler
    def set_dictionary(self, dictionary_file):
        self.dictionary_file = dictionary_file

    def get_dictionary(self):
        return self.dictionary_file

    def read_dictionary(self):
        with open(self.dictionary_file, mode='r', encoding='utf-8') as dictionary:

            conditions_found = False
            condition_definitions = False
            conditional_breaker = '%\n'

            for line in dictionary:
                if line == conditional_breaker:
                    if condition_definitions:
                        conditions_found = True
                        condition_definitions = False
                    else:
                        condition_definitions = True
                elif condition_definitions:
                    line_parse = line.split()
                    self.conditions[line_parse[0]] = line_parse[1]
                else:
                    if not conditions_found:
                        continue
                    else:
                        line_parse = line.split()
                        self.terms[line_parse[0]] = line_parse[1]

            if not conditions_found:
                print('Dictionary CANNOT be read. Check formatting.')

    # Undesired Word List Handler
    def set_undesired_words(self, undesired_list_file):
        self.undesired_list_file = undesired_list_file

    def get_undesired_words(self):
        return self.undesired_list_file

    def read_undesired_words(self):
        with open(self.undesired_list_file, mode='r', encoding='utf-8') as undesired_list:
            for line in undesired_list:
                self.undesired_list.append(line)

    # File Handler
    def set_target_file(self, target_file, file_type):
        self.target_file = target_file
        self.target_type = file_type
        self.target_array = []

    def get_target_file(self):
        return self.target_file

    def read_target_file(self):

        if self.target_file == 'None':
            print('No target file is uploaded.')
        else:
            if self.target_type == '.csv':
                with open(self.target_file, mode='r', encoding='utf-16') as csv_reader:
                    row_num = 0
                    for line in csv_reader:
                        # Remove enter escape character '\n'
                        line = line[:-1]
                        # Split the row based on delimiter '\t'
                        row = line.split(sep='\t')

                        if row_num == 0:
                            header = []
                            for index in range(len(row)):
                                column_num = index + 1
                                column_name = 'Column ' + str(column_num)
                                header.append(column_name)
                            self.target_array.append(header)
                        self.target_array.append(row)
                        row_num += 1

            elif self.target_type == '.txt':
                pass # Not implemented.

    # LIWC Mechanics
    def set_input_target_columns(self, target_columns):
        self.input_target_columns = target_columns

    def set_target_columns(self):
        max_columns = len(self.target_array[0])
        for column_num in self.input_target_columns:
            if column_num <= max_columns:
                self.target_columns.append(column_num - 1)
            else:
                self.target_columns = []
                print('ERROR: Column index out of range.')

    def word_count_analysis(self):
        for index in self.target_columns:
            word_counts = []
            row_num = 0
            for row in self.target_array:
                if row_num == 0:
                    header = ['Word Count (' + str(index + 1) + ')']
                    word_counts.append(header)
                else:
                    string = row[index].split()
                    word_counts.append([len(string)])
                row_num += 1

            self.word_count_columns.append(word_counts)

    def dictionary_analysis(self):
        unwanted_delimiters = ' ,.;:/"?!()<>'
        for column_index in self.target_columns:
            for condition in self.conditions:
                condition_values = []
                row_num = 0
                for row in self.target_array:
                    if row_num == 0:
                        header = [self.conditions[condition] + ' (' + str(column_index + 1) + ')']
                        condition_values.append(header)
                    else:
                        string = row[column_index]
                        replaced_num = 0
                        for undesired_word in self.undesired_list:
                            if undesired_word in string:
                                word_length = len(undesired_word)
                                start_index = 0
                                index = string.find(undesired_word, start_index, len(string))
                                while index != -1:
                                    front_clear = True
                                    back_clear = True
                                    front = index - 1
                                    back = index + word_length
                                    if front:
                                        front_clear = unwanted_delimiters.find(string[front], 0) + 1
                                    if back:
                                        back_clear = unwanted_delimiters.find(string[back], 0) + 1
                                    if front_clear and back_clear:
                                        string = string.replace(undesired_word, '')
                                        replaced_num += 1
                                        start_index = 0
                                    else:
                                        start_index = back
                                    index = string.find(undesired_word, start_index, len(string))

                        string_parse = string.split()
                        word_count = len(string_parse) + replaced_num
                        condition_count = 0
                        for word in string_parse:
                            word = word.lower()
                            if word in self.terms.keys():
                                if self.terms[word] == condition:
                                    condition_count += 1
                        if self.number_representation == 'Fraction':
                            percentage_condition = str(condition_count) + ' of ' + str(word_count)
                            condition_values.append([percentage_condition])
                        else:
                            percentage_condition = round((condition_count/word_count), 4) * 100
                            condition_values.append([percentage_condition])
                    row_num += 1
                self.analysis_columns.append(condition_values)

    def perform_analysis(self):
        self.read_dictionary()
        self.read_target_file()
        self.read_undesired_words()
        self.set_target_columns()

        self.results = self.target_array

        self.word_count_analysis()
        for word_counts in self.word_count_columns:
            self.results = np.hstack((self.results, word_counts))

        self.dictionary_analysis()
        for analysis_count in self.analysis_columns:
            self.results = np.hstack((self.results, analysis_count))

    # API Settings
    def set_number_representation(self, number_representation):
        self.number_representation = number_representation

    # Export Functions
    def export_to_csv(self, csv_name):
        with open(csv_name, mode='w', encoding='utf-16') as csv_writer:
            writer = csv.writer(csv_writer, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for line in self.results:
                writer.writerow(line)


# Moral Foundation Research API Build 1.1
class MoralFoundationsResearchAPI:
    '''
    MoralFoundationsResearchAPI Build v1.1
    Updates
    - Added Mean and Standard Deviation to Statistics Inference Fucntion
    - Added Two Sample T-Test function
    '''

    class NormalizedUserData:

        def __init__(self):
            self.data = []
            self.count = 0

    def __init__(self, liwc_object):
        self.liwc = liwc_object
        self.results = self.liwc.results
        self.normalized_results = []

    def reset_results(self):
        self.results = self.liwc.results

    def get_column(self, index, array=None):
        column = []
        row_num = 0
        header_rows = -1

        if array is None:
            array = self.results
            header_rows = 1

        for row in array:
            if row_num > header_rows:
                column.append(float(row[index]))
            row_num += 1
        return column

    def separate_governor_political_parties(self, political_parties_file):
        error = False
        political_party_dict = {}
        with open(political_parties_file, mode='r') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for line in csv_reader:
                political_party_dict[line[0]] = line[1]

        political_parties = []
        row_num = 0
        for row in self.results:
            user_name = row[0]
            if row_num < 2:
                political_parties.append(['Political Party'])
            elif user_name in political_party_dict.keys():
                political_parties.append([political_party_dict[user_name]])
            else:
                print('ERROR: Missing candidate party association.')
                error = True
                break
            row_num += 1

        if not error:
            self.results = np.hstack((political_parties, self.results))

    def normalize_tweets_by_user(self, user_name_column, target_columns):
        '''
        Normalizes values from target columns. Other columns are copied from the first entry for the user.
        '''

        normalized_user_list = {}
        user_name_column -= 1
        row_num = 0

        # Enter each user_name row as one normalized entry
        for row in self.results:
            if row_num < 2:
                self.normalized_results.append(self.results[row_num])
            else:
                user_name = row[user_name_column]
                if user_name in normalized_user_list.keys():
                    normalized_user_data = normalized_user_list[user_name]
                    for column in target_columns:
                        index = column - 1
                        row_array = [row]
                        normalized_user_data.data[index] = str(
                            (float(normalized_user_data.data[index]) + self.get_column(index, row_array)[0]))
                else:
                    normalized_user_data = self.NormalizedUserData()
                    normalized_user_data.data = row
                    normalized_user_list[user_name] = normalized_user_data
                normalized_user_data.count += 1
            row_num += 1

        for user_name in normalized_user_list:
            row = normalized_user_list[user_name]
            for column in target_columns:
                index = column - 1
                normalized_user_list[user_name].data[index] = str(float(row.data[index])/row.count)

            self.normalized_results.append(normalized_user_list[user_name].data)

    def statistical_inference(self, target_columns):
        mean = []
        stddev = []
        for column in target_columns:
            index = column - 1
            column = self.get_column(index)
            mean.append(statistics.mean(column))
            stddev.append(statistics.stdev(column))

        for index in range(len(target_columns)):
            print('Average for ' + api.results[0][target_columns[index] - 1] + ' is ' + str(
                round(mean[index], 4)))
            print('Standard Deviation for ' + api.results[0][target_columns[index] - 1] + ' is ' + str(
                round(stddev[index], 4)))
            print('')

    def two_sample_t_test(self, condition_column, condition_1, condition_2, target_columns):

        condition_column -= 1

        condition_1_rows = []
        condition_2_rows = []

        # Separate the data into two arrays based on conditions in a column based on the conditions
        for row in self.results:
            condition_element = row[condition_column]
            if condition_element == condition_1:
                condition_1_rows.append(row)
            elif condition_element == condition_2:
                condition_2_rows.append(row)

        # Find the column data values for both conditions and perform t_test
        for column in target_columns:
            index = column - 1

            row_name = self.results[0][index]
            condition_1_column = self.get_column(index, condition_1_rows)
            condition_2_column = self.get_column(index, condition_2_rows)

            t, p = ttest_ind(condition_1_column, condition_2_column, equal_var=False)

            print(row_name)
            print('t = ' + str(t) + '. p = ' + str(p) + '.\n')

    def export_to_csv(self, csv_name):
        with open(csv_name, mode='w', encoding='utf-16') as csv_writer:
            writer = csv.writer(csv_writer, delimiter='\t', quotechar='"', quoting=csv.QUOTE_MINIMAL)
            for line in self.results:
                writer.writerow(line)


if __name__ == "__main__":
    '''
    --------------- Twitter Scraping --------------
    '''
    '''
    # Initialized Variables
    today = DateAndTime().get_current_date()
    since = "2019-12-01"
    limit_per_user = 1000
    input_user_names = 'Input Configuration/user_names.csv'
    input_text_query = 'Input Configuration/text_query.csv'

    twitter_database_api = TwitterDatabaseAPI(input_user_names, input_text_query, begin_date=since,
                                        limit=limit_per_user, debug_mode=True)
    twitter_database_api.export_to_csv('test_1.csv')
    '''

    '''
    --------------- LIWC Analysis ----------------
    '''

    # Initialized Variables
    dictionary = 'Dictionaries/mfd2.0.dic'
    target_file = 'Twitter Databases/test.csv'
    target_type = '.csv'
    target_columns = [3]
    export_file = 'LIWC Analysis Databses/test_analysis_3.csv'
    undesired_list_file = 'Input Configuration/undesired_words.csv'

    # Operations
    liwc = LinguisticInquiryWordCountAPI()

    liwc.set_dictionary(dictionary)
    liwc.set_target_file(target_file, target_type)
    liwc.set_input_target_columns(target_columns)
    liwc.set_undesired_words(undesired_list_file)

    liwc.perform_analysis()

    liwc.export_to_csv(export_file)

    '''
    ------------- Moral Foundations Research ----------
    '''
    api = MoralFoundationsResearchAPI(liwc)

    political_parties_file = 'Input Configuration/political_parties.csv'
    export_file = 'Moral Foundations Databases/test_political_parties_1.csv'
    statistical_inference_columns = [7, 8, 9, 10, 11, 12, 13, 14, 15, 16]

    api.separate_governor_political_parties(political_parties_file)
    api.export_to_csv(export_file)

    api.normalize_tweets_by_user(2, statistical_inference_columns)

    api.results = api.normalized_results

    api.statistical_inference(statistical_inference_columns)
    api.two_sample_t_test(1, 'R', 'D', statistical_inference_columns)

