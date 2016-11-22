import os
import json
import unittest


from pdf_parser import run_pdf_parser

class TestStringMethods(unittest.TestCase):

    def setUp(self):
        PDF_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        # BASE_DIR = os.path.abspath(os.path.dirname(DJANGO_DIR))
        # import ipdb;ipdb.set_trace()
        base_bizfiles_dir = PDF_DIR + '/test_bizfiles'
        self.test_bizfiles_dir = base_bizfiles_dir + '/bizfiles/'
        self.test_bizfiles_json_dir = base_bizfiles_dir + '/bizfiles_json/'
        self.bizfile_names = [file for file in os.listdir(self.test_bizfiles_dir) if file.endswith('.pdf')]

    def test_bizfiles(self):
        for bizfile in self.bizfile_names:
            with open(self.test_bizfiles_dir + bizfile) as bizfile_pdf:
                actual_company_details = run_pdf_parser(bizfile_pdf)
                actual_company_details.pop('pdf_file')
            bizfile_name, extension = os.path.splitext(bizfile)
            bizfile_json_name = self.test_bizfiles_json_dir + bizfile_name + '.json'
            json_bizfile = open(bizfile_json_name)
            expected_company_details = json.load(json_bizfile)
            for key, expected_details in expected_company_details.iteritems():
                if type(expected_details) == list:
                    expected_details.sort()
                    actual_details = actual_company_details[key]
                    actual_details.sort()
                    actual_company_details[key].sort()
                    self.assertEqual(len(actual_details), len(expected_details))
                    self.assertListEqual(actual_details, expected_details)
                else:
                    self.assertEqual(expected_details, actual_company_details[key])

if __name__ == '__main__':
    unittest.main()
