import random
import unittest
from collections import Counter
from typing import List
import tempfile
from lrtc_lib.data_access.core.data_structs import Document, TextElement, Label
from lrtc_lib.data_access.file_based.utils import URI_SEP

from lrtc_lib.data_access.file_based.file_based_data_access import FileBasedDataAccess
from lrtc_lib.data_access.core.data_structs import LABEL_POSITIVE, LABEL_NEGATIVE


def generate_simple_doc(dataset_name, doc_id=0, add_duplicate=False):
    sentences = [f'Document Title is Super Interesting {doc_id}', f'First sentence is not that attractive. {doc_id}',
                 f'The second one is a bit better. {doc_id}',
                 f'Last sentence offers a promising view for the future! {doc_id}']
    if add_duplicate:
        sentences.append('Document Title is Super Interesting '+str(doc_id))
    text_elements = []
    start_span = 0
    for idx, sentence in enumerate(sentences):
        end_span = start_span + len(sentence)
        text_elements.append(TextElement(uri=URI_SEP.join([dataset_name, str(doc_id), str(idx)]), text=sentence,
                                         span=[(start_span, end_span)], metadata={}, category_to_label={}))
        start_span = end_span + 1

    doc = Document(uri=dataset_name + URI_SEP + str(doc_id), text_elements=text_elements, metadata={})
    return doc


def generate_corpus(data_access, dataset_name, num_of_documents=1, add_duplicate=False):
    data_access.delete_dataset(dataset_name)
    docs = [generate_simple_doc(dataset_name, doc_id, add_duplicate) for doc_id in range(0, num_of_documents)]
    data_access.add_documents(dataset_name=dataset_name, documents=docs)
    return docs


def add_random_labels_to_document(doc: Document, min_num_sentences_to_label: int, categories: List[str],seed=0):
    uri_to_label = {}
    random.seed(seed)
    text_elements_to_label = random.sample(doc.text_elements, min(min_num_sentences_to_label, len(doc.text_elements)))
    for elem in text_elements_to_label:
        categories_to_label = random.sample(categories, random.randint(0, len(categories)))
        labels = {cat: Label(label=LABEL_POSITIVE) if cat in categories_to_label else Label(
            label=LABEL_NEGATIVE) for cat in categories}
        uri_to_label[elem.uri] = labels
    return uri_to_label


def add_labels_to_doc(doc: Document, category: str):
    sentences_and_labels = []
    for elem in doc.text_elements:
        labels = {category: Label(label=LABEL_POSITIVE)}
        sentences_and_labels.append((elem.uri, labels))
    return sentences_and_labels


class TestFileBasedDataAccess(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_temp_dir = tempfile.TemporaryDirectory()
        cls.data_access = FileBasedDataAccess(cls.data_temp_dir.name)

    @classmethod
    def tearDownClass(cls):
        cls.data_temp_dir.cleanup()

    def test_add_documents_and_get_documents(self):
        dataset_name = self.test_add_documents_and_get_documents.__name__ + '_dump'
        doc = generate_corpus(self.data_access,dataset_name)[0]
        doc_in_memory = self.data_access.get_documents(None,dataset_name, [doc.uri])[0]
        # compare all fields
        diffs = [(field, getattr(doc_in_memory, field), getattr(doc, field)) for field in
                 Document.__annotations__ if not getattr(doc_in_memory, field) == getattr(doc, field)]
        self.assertEqual(0, len(diffs))
        self.data_access.delete_dataset(dataset_name)

    def test_set_labels_and_get_documents(self):
        workspace_id = 'test_set_labels'
        dataset_name = self.test_set_labels_and_get_documents.__name__ + '_dump'
        categories = ['cat_' + str(i) for i in range(3)]
        doc = generate_corpus(self.data_access,dataset_name)[0]
        uri_to_label = add_random_labels_to_document(doc, 5, categories)
        self.data_access.set_labels(workspace_id, uri_to_label)

        doc_with_labels_info = self.data_access.get_documents(workspace_id, dataset_name, [doc.uri])
        texts_and_labels_dict = dict(uri_to_label)
        for text in doc_with_labels_info[0].text_elements:
            if text.uri in texts_and_labels_dict:
                self.assertDictEqual(text.category_to_label, texts_and_labels_dict[text.uri])
            else:
                self.assertDictEqual(text.category_to_label, {})
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_unset_labels(self):
        workspace_id = 'test_unset_labels'
        dataset_name = self.test_set_labels_and_get_documents.__name__ + '_dump'
        category = "cat1"
        doc = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name)[0]
        texts_and_labels_list = add_labels_to_doc(doc, category)
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, dict(texts_and_labels_list))

        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        self.assertGreater(labels_count[True], 0)
        TestFileBasedDataAccess.data_access.unset_labels(workspace_id, category, [x[0] for x in texts_and_labels_list])
        labels_count_after_unset = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        self.assertEqual(0, labels_count_after_unset[True])
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_all_document_uris(self):
        dataset_name = self.test_get_all_document_uris.__name__ + '_dump'
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, random.randint(1, 10))
        docs_uris_in_memory = TestFileBasedDataAccess.data_access.get_all_document_uris(dataset_name)
        docs_uris_expected = [doc.uri for doc in docs]
        self.assertSetEqual(set(docs_uris_expected), set(docs_uris_in_memory))
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_all_text_elements_uris(self):
        dataset_name = self.test_get_all_text_elements_uris.__name__ + '_dump'
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, random.randint(1, 10))
        text_elements_uris_in_memory = TestFileBasedDataAccess.data_access.get_all_text_elements_uris(dataset_name)
        text_elements_uris_expected = [text.uri for doc in docs for text in doc.text_elements]
        self.assertSetEqual(set(text_elements_uris_expected), set(text_elements_uris_in_memory))
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_all_text_elements(self):
        dataset_name = self.test_get_all_text_elements.__name__ + '_dump'
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, random.randint(1, 10))
        text_elements_found = TestFileBasedDataAccess.data_access.get_all_text_elements(dataset_name)
        text_elements_found.sort(key=lambda t: t.uri)
        text_elements_expected = [text for doc in docs for text in doc.text_elements]
        text_elements_expected.sort(key=lambda t: t.uri)
        self.assertListEqual(text_elements_expected, text_elements_found)

        del TestFileBasedDataAccess.data_access.ds_in_memory[dataset_name]
        # test again after clearing from memory
        text_elements_found = TestFileBasedDataAccess.data_access.get_all_text_elements(dataset_name)
        text_elements_found.sort(key=lambda t: t.uri)
        self.assertListEqual(text_elements_expected, text_elements_found)
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    # def test_get_text_elements(self):
    #     dataset_name = self.test_sample_text_elements.__name__ + '_dump'
    #     sample_size = 5
    #     generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 10)
    #     sampled_texts_res = TestFileBasedDataAccess.data_access.get_text_elements(dataset_name, sample_size)
    #     self.assertEqual(sample_size, len(sampled_texts_res['results']))
    #
    #     sample_all = 10 ** 100  # a huge sample_size to sample all elements
    #     sampled_texts_res = TestFileBasedDataAccess.data_access.get_text_elements(dataset_name, sample_all)
    #     self.assertEqual(sampled_texts_res['hit_count'], len(sampled_texts_res['results']),
    #                      f'the number of sampled elements does not equal to the hit count, '
    #                      f'even though asked to sample all.')
    #     self.assertEqual(len(TestFileBasedDataAccess.data_access.get_all_text_elements_uris(dataset_name)), sampled_texts_res['hit_count'],
    #                      f'the hit count does not equal to the total number of element uris in the dataset, '
    #                      f'even though asked to sample all.')
    #     # assert no labels were added
    #     self.assertDictEqual(sampled_texts_res['results'][0].category_to_label, {})
    #     TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_text_elements(self):
        def sample_and_check_that_labels_match(doc, orig_dict):
            sampled_texts_res = TestFileBasedDataAccess.data_access.get_text_elements(workspace_id, dataset_name, sample_all)
            for doc_text in doc.text_elements:
                sampled_text = [sampled for sampled in sampled_texts_res['results'] if sampled.uri == doc_text.uri]
                self.assertEqual(1, len(sampled_text))
                if sampled_text[0].uri in orig_dict:
                    self.assertDictEqual(sampled_text[0].category_to_label, orig_dict[sampled_text[0].uri],
                                         f'for text {doc_text}')
                else:
                    self.assertDictEqual(sampled_text[0].category_to_label, {}, f'for text {doc_text}')

        workspace_id = 'test_sample_text_elements'
        dataset_name = self.test_get_text_elements.__name__ + '_dump'
        sample_all = 10 ** 100  # a huge sample_size to sample all elements
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 5)
        # add labels info for a single doc
        selected_doc = docs[0]
        texts_and_labels_dict = dict(add_random_labels_to_document(selected_doc, 3, ['Autobots', 'Decepticons']))
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, texts_and_labels_dict)


        sample_and_check_that_labels_match(selected_doc, texts_and_labels_dict)
        del TestFileBasedDataAccess.data_access.ds_in_memory[dataset_name]
        # check again after clearing from memory
        sample_and_check_that_labels_match(selected_doc, texts_and_labels_dict)
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_unlabeled_text_elements(self):
        workspace_id = 'test_sample_unlabeled_text_elements'
        dataset_name = self.test_get_unlabeled_text_elements.__name__ + '_dump'
        category = 'Autobots'
        sample_all = 10 ** 100  # a huge sample_size to sample all elements
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 2)
        # add labels info for a single doc
        selected_doc = docs[0]
        texts_and_labels_list = add_random_labels_to_document(selected_doc, 5, [category])
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, texts_and_labels_list)

        sampled_texts_res = TestFileBasedDataAccess.data_access.get_unlabeled_text_elements(workspace_id, dataset_name, category, sample_all)
        for sampled_text in sampled_texts_res['results']:
            self.assertDictEqual(sampled_text.category_to_label, {})
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_labeled_text_elements(self):
        workspace_id = 'test_sample_labeled_text_elements'
        dataset_name = self.test_get_labeled_text_elements.__name__ + '_dump'
        category = 'Decepticons'
        sample_all = 10 ** 100  # a huge sample_size to sample all elements
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 2)
        # add labels info for a single doc
        selected_doc = docs[0]
        texts_and_labels_list = add_random_labels_to_document(selected_doc, 5, [category])
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, texts_and_labels_list)
        texts_and_labels_dict = dict(texts_and_labels_list)

        sampled_texts_res = TestFileBasedDataAccess.data_access.get_labeled_text_elements(workspace_id, dataset_name, category, sample_all)
        self.assertEqual(len(texts_and_labels_list), len(sampled_texts_res['results']),
                         f'all and only the {len(texts_and_labels_list)} labeled elements should have been sampled.')

        for sampled_text in sampled_texts_res['results']:
            self.assertIn(sampled_text.uri, texts_and_labels_dict.keys(),
                          f'the sampled text uri - {sampled_text.uri} - was not found in the '
                          f'texts that were labeled: {texts_and_labels_dict}')
            self.assertDictEqual(sampled_text.category_to_label, texts_and_labels_dict[sampled_text.uri])
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_sample_by_query_text_elements(self):
        workspace_id = 'test_sample_by_query_text_elements'
        dataset_name = self.test_sample_by_query_text_elements.__name__ + '_dump'
        category = 'Autobots'
        query = 'sentence'
        sample_all = 10 ** 100  # a huge sample_size to sample all elements
        doc = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 1)[0]
        # doc's elements = ['Document Title is Super Interesting', 'First sentence is not that attractive.',
        #          'The second one is a bit better.', 'Last sentence offers a promising view for the future!']
        # add labels info for a single doc
        uri_to_label_dict = {doc.text_elements[0].uri: {category: Label(label=LABEL_POSITIVE)},  # 1st sent does not match query
            doc.text_elements[1].uri: {category: Label(label=LABEL_POSITIVE)} } # 2nd sent does match query

        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict)

        # query + unlabeled elements
        sampled_texts_res = TestFileBasedDataAccess.data_access.get_unlabeled_text_elements(workspace_id, dataset_name, category, sample_all)
        for sampled_text in sampled_texts_res['results']:
            self.assertDictEqual(sampled_text.category_to_label, {})

        # query + labeled elements
        sampled_texts_res = TestFileBasedDataAccess.data_access.get_labeled_text_elements(workspace_id, dataset_name, category, sample_all,
                                                                     query)
        self.assertEqual(1, len(sampled_texts_res['results']),
                         f'all and only the {len(uri_to_label_dict)} labeled elements should have been sampled.')

        for sampled_text in sampled_texts_res['results']:
            self.assertIn(sampled_text.uri, uri_to_label_dict.keys(),
                          f'the sampled text uri - {sampled_text.uri} - was not found in the '
                          f'texts that were labeled: {uri_to_label_dict}')
            self.assertIn(query, sampled_text.text)
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_query_text_elements_pagination(self):
        workspace_id = 'test_sample_by_query_text_elements'
        dataset_name = self.test_sample_by_query_text_elements.__name__ + '_dump'
        category = 'Autobots'
        query = 'sentence'
        sample_all = 10 ** 100  # a huge sample_size to sample all elements
        generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 5)

        # query no limit
        sampled_texts_res = TestFileBasedDataAccess.data_access.get_unlabeled_text_elements(workspace_id, dataset_name, category, sample_all)
        self.assertEqual(20, len(sampled_texts_res['results']),
                         f"20 elements should have been sampled.")

        second_element_uri = sampled_texts_res["results"][1].uri
        sampled_texts_res = TestFileBasedDataAccess.data_access.get_unlabeled_text_elements(workspace_id, dataset_name, category, sample_all,
                                                                       sample_start_idx=1)
        self.assertEqual(19, len(sampled_texts_res['results']),
                         f'19 elements should have been sampled.')

        self.assertEqual(second_element_uri,sampled_texts_res['results'][0].uri,"when using sample_start_idx=1,"
                                                                                "the first element should be the second element without paging")

        sampled_texts_res = TestFileBasedDataAccess.data_access.get_unlabeled_text_elements(workspace_id, dataset_name, category, sample_all,
                                                                       sample_start_idx=20)
        self.assertEqual(0, len(sampled_texts_res['results']),
                         "when sample_start_idx=number_of_elements, no element should return")

        TestFileBasedDataAccess.data_access.delete_all_labels(workspace_id,dataset_name)
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)
        # texts_and_labels_dict = dict(texts_and_labels_list)
        # for sampled_text in sampled_texts_res['results']:
        #     self.assertIn(sampled_text.uri, texts_and_labels_dict.keys(),
        #                   f'the sampled text uri - {sampled_text.uri} - was not found in the '
        #                   f'texts that were labeled: {texts_and_labels_dict}')
        #     self.assertIn(query, sampled_text.text)
        # TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_multithread_async_set_labels(self):
        import threading
        NUM_DOCS = 100
        workspace_id = 'test_multithread_set_labels'
        dataset_name = self.test_multithread_async_set_labels.__name__ + '_dump'
        category = 'Decepticons'
        categories = [category]
        corpus = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, num_of_documents=NUM_DOCS)
        batch_size = 10

        threads = []
        results = [None]*int(NUM_DOCS/batch_size)
        i = 0
        for begin in range(0, NUM_DOCS, batch_size):
            end = min(begin + batch_size, NUM_DOCS)
            x = threading.Thread(target=self.set_labels_thread, args=(categories, category, corpus,
                                   workspace_id,begin,end,i,results))
            i += 1
            threads.append(x)
            x.start()
        for thread in threads:
            thread.join()
        all_from_threads = Counter()
        for d in results:
            all_from_threads.update(d)
        self.assertDictEqual(dict(all_from_threads),dict(TestFileBasedDataAccess.data_access.get_label_counts(workspace_id,dataset_name,category)))
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def set_labels_thread(self, categories, category, corpus, workspace_id,start, stop, idx, results):
        sentences_and_labels_all ={}
        for doc in corpus[start:stop]:
            texts_and_labels_list = add_random_labels_to_document(doc, 5, categories)
            TestFileBasedDataAccess.data_access.set_labels(workspace_id, texts_and_labels_list)
            sentences_and_labels_all.update(texts_and_labels_list)
        true_count = len([1 for _,label_dict in sentences_and_labels_all.items() if label_dict[category].label == LABEL_POSITIVE])
        false_count = len([1 for _,label_dict in sentences_and_labels_all.items() if label_dict[category].label == LABEL_NEGATIVE])
        results[idx] =  {LABEL_POSITIVE:true_count,LABEL_NEGATIVE:false_count}

    def test_get_label_counts(self):
        workspace_id = 'test_get_label_counts'
        dataset_name = self.test_get_label_counts.__name__ + '_dump'
        category_to_count = 'Decepticons'
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 2)
        # add labels info for a single doc
        selected_doc = docs[0]
        uri_to_label_dict = add_random_labels_to_document(selected_doc, 5, [category_to_count,"another category 1", "another category 2"])
        # if texts_and_labels_list:
        #     if category in texts_and_labels_list[0][1]:
        #         texts_and_labels_list[0][1][category].label = LABEL_NEGATIVE
        #     else:
        #         texts_and_labels_list[0][1][category] = Label(label=LABEL_NEGATIVE)
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict)

        category_label_counts = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category_to_count)
        for label_val, observed_count in category_label_counts.items():
            expected_count = len(
                [label for id,label in uri_to_label_dict.items() if category_to_count in label and label_val == label[category_to_count].label]) ## TODO verify
            self.assertEqual(expected_count, observed_count, f'count for {label_val} does not match.')
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_get_text_elements_by_id(self):
        workspace_id = "test_get_text_elements_by_id"
        dataset_name = self.test_get_text_elements_by_id.__name__ + '_dump'
        categories = ['cat_' + str(i) for i in range(3)]
        docs = generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 2)
        doc = docs[0]
        texts_and_labels_list = add_random_labels_to_document(doc, 5, categories)  # [(uri, {category: Label})]
        uri_to_labels = dict(texts_and_labels_list)
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, texts_and_labels_list)
        uris = [x.uri for doc in docs for x in doc.text_elements]
        uris = [uris[2], uris[0], uris[1]]  # using different order to test if order is preserved

        all_elements = TestFileBasedDataAccess.data_access.get_text_elements_by_uris(workspace_id, dataset_name, uris)
        self.assertEqual(len(uris), len(all_elements))
        self.assertEqual(uri_to_labels[uris[0]], all_elements[0].category_to_label)
        self.assertEqual(uri_to_labels[uris[1]], all_elements[1].category_to_label)

        del TestFileBasedDataAccess.data_access.ds_in_memory[dataset_name]
        # test again after clearing from memory
        all_elements = TestFileBasedDataAccess.data_access.get_text_elements_by_uris(workspace_id, dataset_name, uris)
        self.assertEqual(len(uris), len(all_elements))
        self.assertEqual(uri_to_labels[uris[0]], all_elements[0].category_to_label)
        self.assertEqual(uri_to_labels[uris[1]], all_elements[1].category_to_label)

        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)

    def test_duplicates_removal(self):
        workspace_id = 'test_duplicates_removal'
        dataset_name = self.test_duplicates_removal.__name__ + '_dump'
        generate_corpus(TestFileBasedDataAccess.data_access,dataset_name, 1, add_duplicate=True)
        category = 'cat1'
        all_elements = sorted(TestFileBasedDataAccess.data_access.get_all_text_elements(dataset_name),key=lambda te:te.uri)
        all_elements2 = sorted(TestFileBasedDataAccess.data_access.get_text_elements(workspace_id, dataset_name, 10**6, remove_duplicates=False)['results'],key=lambda te:te.uri)
        self.assertListEqual(all_elements, all_elements2)
        all_without_dups = TestFileBasedDataAccess.data_access.get_text_elements(workspace_id, dataset_name, 10**6, remove_duplicates=True)['results']
        self.assertEqual(len(all_elements), len(all_without_dups)+1)

        # 1. test propagation of labels:
        uri_to_label_dict = {elem.uri: {category: Label(label=LABEL_POSITIVE)}
                                 for elem in all_without_dups}
        # set labels without propagating to duplicates
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict, apply_to_duplicate_texts=False)
        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        self.assertEqual(labels_count[LABEL_POSITIVE], len(all_without_dups))
        # unset labels
        TestFileBasedDataAccess.data_access.unset_labels(workspace_id, category, [elem.uri for elem in all_without_dups])
        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        self.assertEqual(labels_count[LABEL_POSITIVE], 0)
        # set labels with propagating to duplicates
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict, apply_to_duplicate_texts=True)
        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        self.assertEqual(labels_count[LABEL_POSITIVE], len(all_elements))
        TestFileBasedDataAccess.data_access.unset_labels(workspace_id, category, [elem.uri for elem in all_elements])

        # 2. test sampling of duplicate examples:
        non_representative_duplicates = [x for x in all_elements if x not in all_without_dups]
        uri_to_label_dict = {elem.uri: {category: Label(label=LABEL_POSITIVE)}
                                 for elem in non_representative_duplicates}
        # set labels without propagating to duplicates
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict, apply_to_duplicate_texts=False)
        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        sampled = TestFileBasedDataAccess.data_access.get_labeled_text_elements(workspace_id, dataset_name, category, 10**6,
                                                           remove_duplicates=True)['results']
        self.assertEqual(labels_count[LABEL_POSITIVE], len(sampled), len(non_representative_duplicates))
        # set labels with propagating to duplicates
        TestFileBasedDataAccess.data_access.set_labels(workspace_id, uri_to_label_dict, apply_to_duplicate_texts=True)
        labels_count = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category)
        sampled = TestFileBasedDataAccess.data_access.get_labeled_text_elements(workspace_id, dataset_name, category, 10 ** 6,
                                                           remove_duplicates=True)['results']
        self.assertGreater(labels_count[LABEL_POSITIVE], len(non_representative_duplicates))
        labels_count_no_dups = TestFileBasedDataAccess.data_access.get_label_counts(workspace_id, dataset_name, category,
                                                            remove_duplicates=True)
        self.assertEqual(labels_count_no_dups[LABEL_POSITIVE], len(sampled), len(non_representative_duplicates))
        TestFileBasedDataAccess.data_access.delete_all_labels(workspace_id,dataset_name)
        TestFileBasedDataAccess.data_access.delete_dataset(dataset_name)


if __name__ == "__main__":
    unittest.main()
