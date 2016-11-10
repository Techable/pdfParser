#!/usr/bin/env python
#Standard imports
from datetime import datetime
import re

#Imports related to pdfminer
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdftypes import PDFObjRef
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.converter import PDFPageAggregator
from collections import defaultdict, namedtuple

# default configuration dictionary which will be initialized when
# PdfParser objects are created

DEFAULTS = {"input_pdf_file": "testcases/inputfile7.pdf"}

# dictionary of configured values
conf = {}
TextBlock= namedtuple("TextBlock", ["x", "y", "z", "text"])

class PdfParserException(Exception):
    """ 
    Generic exception for Parsing operations 
    """
    def __init__(self):
        pass

class PdfParser:

    """
    This provides object to encapsulate metadata about Python parser
    """
    def __init__(self, conf):

        """
        Initialize the `PdfParser` config values.
        Contains dictionary of config values.
        """

        # Where all the output text from the pdf parser is stored. 
        #Initialize output text as key value pairs

        self.parsed_output_text = {}
        self.horizontal_dict = defaultdict(lambda : defaultdict(list))
        # Innitializing the input PDF file
        self.input_pdf_file = conf.get("input_pdf_file",  \
                              DEFAULTS["input_pdf_file"])

        self.horizontal_table = defaultdict(list)
        #TODO: Bad design, need to redesign it again
        self.page_number = 0

        #initializing all the fields as blank for now
        self.company_record = {
                'id':'',
                'description':'',
                'bizfile_date':'',
                'receipt_no' : '',
                'registration_no':'',
                'company_name': '',
                'former_name':'',
                'incorp_date':'',
                'company_type':'',
                'status': '',
                'status_date':'',
                'activities_1':'',
                'activites_description':'',
                'activities_2':'',
                'activites_description_2':'',
                'registered_office_address':'',
                'date_of_address':'',
                'date_of_last_agm':'',
                'date_of_last_ar':'',
                'date_of_ac_at_last':'',
                'date_of_lodgment_of_ar':'',
                'audit_firm_name':'',
                'organization':'',
            }
        self.charges = []
        self.capital_details = []
        self.paidup_capital_details = []
        self.shareholders_details = []
        self.shareholder_type_details = []
        self.officers_details = []
        self.pending_officers_table = None
        self.pending_shareholders_table = None
        self.pending_shareholders_type_table = None
        self.shareholder_type = None
        self.ordinary_num = None
        self.currency = None

class PdfParserProvider:

    """
    This class is used to provide the implementation for the PdfParser class
    """
    def load_pdf_file(self,parser_obj):

        # Open the PDF file
        file_obj = open(parser_obj.input_pdf_file,'rb')

        # Create the parser object associated with the file object
        pdf_parser_obj = PDFParser(file_obj)

        # Create the pdf document object that stores the
        # document structure
        document_obj = PDFDocument(pdf_parser_obj)

        # Connect the parser and the document objects
        pdf_parser_obj.set_document(document_obj)

        # document_obj.set_parser(parser_obj)

        # Create a resource manager object that stores
        # shared resources
        resource_manager_obj = PDFResourceManager()

        #Set parameters for analysis
        laparams = LAParams(detect_vertical=True, all_texts=True, line_margin=0.1)

        #laparams = LAParams(detect_vertical=True,line_margin=0.3)
        #Create PDF aggregator object
        pdf_aggregator_obj = PDFPageAggregator(resource_manager_obj, \
                                                  laparams=laparams)

        # Create a PDF interpreter object.
        interpreter_obj = PDFPageInterpreter(resource_manager_obj, \
                                               pdf_aggregator_obj)

        # Create page aggregator object
        # Process each page contained in the document.
        for page_num, page in enumerate(PDFPage.create_pages(document_obj)):
            interpreter_obj.process_page(page)
            if page.annots:
                self._build_annotations(page)
            page_text = self._get_text(parser_obj, pdf_aggregator_obj, page_num)
            parser_obj.page_number = page_num
            #TODO: Need to copy the data into parsed_output_text variable
            parser_obj.parsed_output_text[page_num + 1] = page_text

    """
    To fetch the text from the pdf_aggregator_obj
    """
    def _get_text(self, parser_obj, pdf_aggregator_obj, page_num):
        temporary_text = []
        layout = pdf_aggregator_obj.get_result()
        for layout_obj in layout:
            if isinstance( layout_obj, LTTextBoxHorizontal ):
                if layout_obj.get_text().strip():
                    layout_obj_y1 = round(((1000 * parser_obj.page_number) + \
                                    layout_obj.y1),2)
                    layout_obj_z = round(layout_obj.height, 2)
                    temporary_text.append( TextBlock(layout_obj.x0, \
                            layout_obj_y1, layout_obj_z, layout_obj.get_text().strip()) )
                    #TODO: Not the pythonic way to write the code
                    #Need to fix it
                    page_nos = parser_obj.horizontal_dict.keys()
                    keys = [parser_obj.horizontal_dict[pageno].keys() for pageno in page_nos]
                    if layout_obj_y1 in keys:
                        parser_obj.horizontal_dict[page_num][layout_obj_y1].append( \
                                TextBlock(layout_obj.x0, layout_obj_y1, layout_obj_z, layout_obj.get_text().strip()))
                    elif (layout_obj_y1 + 4) in keys:
                        parser_obj.horizontal_dict[page_num][layout_obj_y1 + 4].append( \
                                TextBlock(layout_obj.x0, layout_obj_y1, layout_obj_z, layout_obj.get_text().strip()))
                    elif (layout_obj_y1 - 4) in keys:
                        parser_obj.horizontal_dict[page_num][layout_obj_y1 - 4].append( \
                                TextBlock(layout_obj.x0, layout_obj_y1, layout_obj_z, layout_obj.get_text().strip()))
                    else:
                        parser_obj.horizontal_dict[page_num][layout_obj_y1].append(
                             TextBlock(layout_obj.x0, layout_obj_y1, layout_obj_z, layout_obj.get_text().strip()))

        #Appending the key value pairs in the dictionary
        page_values = parser_obj.horizontal_dict[page_num]
        self.populate_company_record_table(parser_obj, page_values)
        self.populate_charges_record_table(parser_obj, page_values)
        self.populate_share_capital_table(parser_obj, page_values)
        self.populate_paidup_capital_table(parser_obj, page_values)
        self.populate_officers_and_representatives(parser_obj, page_values)
        self.populate_shareholders_table(parser_obj, page_values)
        self.populate_shareholder_type_table(parser_obj, page_values)
        return temporary_text



    """
    Populate the table containing charges
    """
    def populate_charges_record_table(self, parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            if 'Charge No.' in values:
                index = self.get_proper_index(key, 28.34, [28.37], page_values)
                records_id = 0
                #To check if the Charges table is empty
                if index in page_values:
                    charge_table_fields = \
                        len(page_values[index])
                else:
                    charge_table_fields = 0

                while(charge_table_fields == 4):
                    charge_ids = [charge['charge_no'] \
                        for charge in parser_obj.charges]
                    charge_no = page_values[index][0].text
                    if index in page_values:

                        charges_dict = {'id':'',
                                        'charge_no':'',
                                        'date_registered':'',
                                        'currency':'',
                                        'amount_secured':'',
                                        'charge_org':''}

                        charges_dict['charge_no'] = charge_no
                        date_registered_str = page_values[index][1].text
                        charges_dict['date_registered'] = datetime.strptime(date_registered_str, '%d/%m/%Y') if date_registered_str else None
                        charges_dict['amount_secured'] = page_values[index][2].text
                        charges_dict['charge_org'] = page_values[index][3].text
                        parser_obj.charges.append(charges_dict)
                        records_id = records_id + 1
                        index = self.get_index(index, 36, [24, 28, 48, 36, 26], page_values)
                    if index in page_values:
                        charge_table_fields = \
                            len(page_values[index])
                    else:
                        break

        # remove duplicates of charges
        parser_obj.charges = [dict(t) for t in set([tuple(d.items()) for d in parser_obj.charges])]

    def get_index(self, index, default_index, possible_deltas, page_values):
        temp_index = [round(index - delta, 2) for delta in possible_deltas if round(index - delta, 2) in page_values]
        if temp_index:
            index = temp_index[0]
        else:
            index = round((index-default_index),2)
        return index

    def update_pending_shareholders_table(self, parser_obj, page_values, index):
        """
        updates the pending shareholders table by looking at address and ordinary number consecutively.
        Also updates the index with the next table row after populating the pending table
        """
        pending_table = parser_obj.pending_shareholders_table
        if index in page_values:
            if index in page_values and not pending_table['address'] and len(page_values[index]) == 1:
                pending_table['address'] = page_values[index][0].text
                index = self.get_index(index, 81, [21, 24, 48, 58, 70, 99, 1495], page_values)
            if(len(page_values[index]) == 2) and pending_table['ordinary_num'] is None:
                pending_table['ordinary_num'] = page_values[index][0].text
                pending_table['currency'] = page_values[index][1].text
                index = self.get_index(index, 81, [21, 24, 48, 47, 58, 70, 99, 1495], page_values)
            if(len(page_values[index]) == 2) and pending_table['pref_num'] is None:
                pending_table['pref_num'] = page_values[index][0].text
                pending_table['pref_currency'] = page_values[index][1].text
                index = self.get_index(index, 81, [21, 24, 48, 58, 70, 99, 1495], page_values)
            parser_obj.shareholders_details.append(pending_table)
            parser_obj.pending_shareholders_table = None
        return index

    """
    Populate the table containing shareholders object
    """
    def populate_shareholders_table(self, parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            if 'Shareholder(s)' in values:
                index = self.get_index(key, 74.34, [97.34, 121.34], page_values)
                records_id = 0
                #To check if the Charges table is empty
                if index in page_values:
                    shareholders_table_fields = \
                        len(page_values[index])
                else:
                    shareholders_table_fields = 0

                while(shareholders_table_fields in [6, 5, 1, 2]):
                    if index in page_values:
                        shareholders_dict = {'name':'',
                                            'address':'',
                                            'shareholder_id':'',
                                            'nationality':'',''
                                            'source_of_address':'',
                                            'address_changed':None,
                                            'currency':'',
                                            'pref_num': None,
                                            'pref_currency': None,
                                            'ordinary_num':None,
                                            'company_record':''}

                        if parser_obj.pending_shareholders_table is None:
                            # TODO this is a bad fix to detect table end in one of the pdfs
                            try:
                                shareholders_dict['shareholder_id'] = page_values[index][2].text
                            except:
                                break
                        shareholders_table_fields == len(page_values[index])
                        if(shareholders_table_fields == 6) or \
                           (shareholders_table_fields == 5):
                            shareholders_dict['name'] = page_values[index][1].text
                            shareholders_dict['nationality'] = page_values[index][3].text
                            shareholders_dict['source_of_address'] = page_values[index][4].text
                            index = round(index-27.0, 2)

                        if not index in page_values:
                            index = round(index  - 10, 2)

                        if parser_obj.pending_shareholders_table:
                            index = self.update_pending_shareholders_table(parser_obj, page_values, index)
                            if index in page_values:
                                shareholders_table_fields = len(page_values[index])
                                continue
                            else:
                                break

                        if (index in page_values):
                            shareholders_table_fields = len(page_values[index])
                            if (shareholders_table_fields == 1):
                                shareholders_dict['address'] = page_values[index][0].text
                        #     elif (shareholders_table_fields == 2):
                        #         shareholders_dict['ordinary_num'] = page_values[index][0].text
                        #         shareholders_dict['currency'] = page_values[index][1].text

                        index = self.get_index(index, 81, [21, 31, 24, 48, 43, 54, 58, 70, 99, 1495], page_values)

                        if index not in page_values:
                            parser_obj.pending_shareholders_table = shareholders_dict
                            break
                        if (index in page_values):
                            shareholders_table_fields = len(page_values[index])
                            if(shareholders_table_fields == 2):
                                pref_index = round(index - 47, 2)
                                if "Ordinary(Number)" in page_values[index][0].text:
                                    index = round(index - 27, 2)
                                    shareholders_dict['ordinary_num'] = page_values[index][0].text
                                    shareholders_dict['currency'] = page_values[index][1].text
                                if pref_index in page_values and 'Preference(Number)' in page_values[pref_index][0].text:
                                    index = round(pref_index - 27, 2)
                                    shareholders_dict['pref_num'] = page_values[index][0].text
                                    shareholders_dict['pref_currency'] = page_values[index][1].text
                        else:
                            parser_obj.pending_shareholders_table = shareholders_dict
                            break

                        parser_obj.shareholders_details.append(shareholders_dict)
                        records_id = records_id + 1
                        index = self.get_index(index, 24, [71], page_values)

                    if index in page_values:
                        shareholders_table_fields = len(page_values[index])
                    else:
                        break
        parser_obj.shareholders_details = \
            [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.shareholders_details])]

    def _find_shareholder_type_and_index(self, list_of_t):
        shareholder_index = None
        shareholder_type = None
        for t in list_of_t:
            shareholder_type_match = re.match(r"Group Share : ([A-Z]) \(Shares co-owned by shareholders listed under this group\)", t.text)
            shareholder_type = shareholder_type_match.group(1) if shareholder_type_match else None
            shareholder_index = t.y
        return shareholder_type, shareholder_index

    def update_pending_shareholder_type(self, list_of_t, page_values, parser_obj):
        """
        need to fix this function for handling pending table values
        """
        if len(list_of_t) == 1:
            # TODO this should be dynamic instead of hardcoding
            expected_headings = ["WHILST EVERY ENDEAVOR IS MADE TO ENSURE THAT INFORMATION PROVIDED IS UPDATED AND CORRECT. THE AUTHORITY"]
            if list_of_t[0].text in expected_headings:
                temp_index = self.get_index(list_of_t[0].y, 99.73, [48.40, 24.34], page_values)
                # TODO this function needs to be fixed to hanlde pending table values
                pending_table = parser_obj.pending_shareholders_type_table
                temp_page_values = page_values.copy()

                temp_shareholder_type = pending_table['shareholder_type'] if pending_table is not None else parser_obj.shareholder_type
                if pending_table is not None and temp_index in temp_page_values and not pending_table['address'] and pending_table['name']:
                    pending_table['address'] = temp_page_values[temp_index][0].text
                    parser_obj.shareholder_type_details.append(pending_table)
                    temp_index = round(temp_index - 58, 2)
                    parser_obj.pending_shareholders_type_table = None
                elif pending_table is not None and not pending_table['name']:
                    temp_index = round(list_of_t[0].y - 95.73, 2)
                    parser_obj.pending_shareholders_type_table = None

                if temp_index in page_values and parser_obj.shareholder_type is not None:
                    page_values[temp_index].sort()
                    pending_shareholder = page_values[temp_index]
                    shareholder_type_table_fields = len(page_values[temp_index])
                    shareholder_type_values = [shareholder for shareholder in parser_obj.shareholder_type_details if temp_shareholder_type == shareholder['shareholder_type']]
                    next_shareholder_type = pending_shareholder[0].text
                    # start of the shareholder type table
                    if(shareholder_type_table_fields == 2):
                        if "Ordinary(Number)" in temp_page_values[temp_index][0].text:
                            temp_index = round(temp_index - 27, 2)
                        ordinary_num = temp_page_values[temp_index][0].text
                        currency = temp_page_values[temp_index][1].text
                        parser_obj.ordinary_num = ordinary_num
                        parser_obj.currency = currency
                        temp_index = self.get_index(temp_index, 81, [21, 23, 24, 25, 48, 51, 58, 70, 99, 1495], temp_page_values)
                        next_shareholder_type = temp_page_values[temp_index][0].text
                        shareholder_type_table_fields = len(temp_page_values[temp_index])
                    if int(next_shareholder_type) == len(shareholder_type_values) + 1:
                        while(shareholder_type_table_fields == 6) or \
                           (shareholder_type_table_fields == 5):
                            shareholder_type_dict = {
                                'name':'',
                                'address':'',
                                'shareholder_id':'',
                                'shareholder_type': temp_shareholder_type,
                                'nationality':'',
                                'source_of_address':'',
                                'address_changed':None,
                                'currency': parser_obj.currency,
                                'ordinary_num': parser_obj.ordinary_num,
                                'company_record':''
                            }
                            shareholder_type_details = temp_page_values[temp_index]
                            shareholder_type_details.sort()
                            shareholder_type_dict['name'] = shareholder_type_details[1].text
                            shareholder_type_dict['shareholder_id'] = shareholder_type_details[2].text
                            shareholder_type_dict['nationality'] = shareholder_type_details[3].text
                            shareholder_type_dict['source_of_address'] = shareholder_type_details[4].text
                            temp_index = round(temp_index-27.0, 2)
                            shareholder_type_dict['address'] = temp_page_values[temp_index][0].text
                            temp_index = self.get_index(temp_index, 81, [25, 47, 35, 58], temp_page_values)
                            parser_obj.shareholder_type_details.append(shareholder_type_dict)
                            shareholder_type_table_fields = len(temp_page_values[temp_index])

    """
    Populate the table containing shareholder type
    """
    def populate_shareholder_type_table(self, parser_obj, page_values):
        temp_page_values = page_values.copy()
        # sorted(temp_page_values.iteritems(), key=lambda (x, y): float(x))
        from collections import OrderedDict
        temp_page_values = OrderedDict(sorted(temp_page_values.iteritems(), key=lambda (x,y): float(x), reverse=True))
        for key, list_of_t in temp_page_values.iteritems():
            self.update_pending_shareholder_type(list_of_t, page_values, parser_obj)
            shareholder_type, shareholder_index = self._find_shareholder_type_and_index(list_of_t)
            for k, list_of_t in temp_page_values.iteritems():
                print k, list_of_t
            if shareholder_type:
                parser_obj.shareholder_type = shareholder_type
                index = self.get_index(shareholder_index, 23, [23], page_values)
                shareholder_type_table_fields = len(temp_page_values[index]) if index in temp_page_values else 0

                if shareholder_type_table_fields == 0 and parser_obj.pending_shareholders_type_table is None:
                    shareholder_type_dict = {
                        'name': '',
                        'address': '',
                        'shareholder_id': '',
                        'shareholder_type': shareholder_type,
                        'nationality': '',
                        'source_of_address': '',
                        'address_changed':None,
                        'currency': '',
                        'ordinary_num': '',
                        'company_record':''
                    }
                    parser_obj.pending_shareholders_type_table = shareholder_type_dict

                # start of the shareholder type table
                if(shareholder_type_table_fields == 2):
                    if "Ordinary(Number)" in temp_page_values[index][0].text:
                        index = round(index - 27, 2)
                    ordinary_num = temp_page_values[index][0].text
                    currency = temp_page_values[index][1].text
                    parser_obj.ordinary_num = ordinary_num
                    parser_obj.currency = currency
                    index = self.get_index(index, 81, [21, 23, 24, 25, 48, 51, 58, 70, 99, 1495], temp_page_values)
                    shareholder_type_table_fields = len(temp_page_values[index])

                    # list of values of shareholder type
                    while(shareholder_type_table_fields == 6) or \
                       (shareholder_type_table_fields == 5):
                        shareholder_type_dict = {
                            'name':'',
                            'address':'',
                            'shareholder_id':'',
                            'shareholder_type':shareholder_type,
                            'nationality':'',
                            'source_of_address':'',
                            'address_changed':None,
                            'currency':currency,
                            'ordinary_num':ordinary_num,
                            'company_record':''
                        }
                        shareholder_type_details = temp_page_values[index]
                        shareholder_type_details.sort()
                        shareholder_type_dict['name'] = shareholder_type_details[1].text
                        shareholder_type_dict['shareholder_id'] = shareholder_type_details[2].text
                        shareholder_type_dict['nationality'] = shareholder_type_details[3].text
                        shareholder_type_dict['source_of_address'] = shareholder_type_details[4].text
                        index = round(index-27.0, 2)
                        if index in page_values and len(temp_page_values[index]) == 1:
                            shareholder_type_dict['address'] = temp_page_values[index][0].text
                            parser_obj.shareholder_type_details.append(shareholder_type_dict)
                        else:
                            parser_obj.pending_shareholders_type_table = shareholder_type_dict
                            break
                        index = self.get_index(index, 81, [25, 47, 35, 58], temp_page_values)
                        if index not in temp_page_values:
                            break
                        shareholder_type_table_fields = len(temp_page_values[index])


    """
    Populate the Capital Details table
    """
    def populate_share_capital_table(self,parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            if 'Capital' in values:
                index = self.get_proper_index(key, 75.34, [75.37], page_values)
                records_id = 0
                #To check if the Charges table is empty
                if index in page_values:
                    capital_table_fields = \
                        len(page_values[index])
                else:
                    capital_table_fields = 0

                while((capital_table_fields == 4) or \
                      (capital_table_fields == 3)):
                    capital_ids = [capital['amount'] \
                        for capital in parser_obj.capital_details]
                    amount = page_values[index][0].text
                    if index in page_values:
                        capital_dict = {'id':'',
                                        'capital_type':'capital',
                                        'amount':'',
                                        'shares': None,
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['shares'] = float(page_values[index][0].text)
                        capital_dict['currency'] = page_values[index][1].text
                        capital_dict['share_type'] = page_values[index][2].text
                        parser_obj.capital_details.append(capital_dict)
                        records_id = records_id + 1
                        index = round(index - 26, 2)
                    if index in page_values:
                        capital_table_fields = \
                            len(page_values[index])
                    else:
                        break
        parser_obj.capital_details = [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.capital_details])]

    """
    Populate the Paidup Capital Details table
    """
    def populate_paidup_capital_table(self,parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            if 'Paid-Up Capital' in values:
                index = self.get_proper_index(key, 50.34, [50.37], page_values)
                records_id = 0
                #To check if the Charges table is empty
                if index in page_values:
                    capital_table_fields = len(page_values[index])
                else:
                    capital_table_fields = 0

                while(capital_table_fields == 3):
                    amount = page_values[index][0].text
                    if index in page_values:
                        capital_dict = {'id':'',
                                        'capital_type':'paid_up_capital',
                                        'amount':'',
                                        'shares':None,
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['currency'] = page_values[index][1].text
                        capital_dict['share_type'] = page_values[index][2].text
                        parser_obj.paidup_capital_details.append(capital_dict)
                        records_id = records_id + 1
                        index = round(index - 26, 2)
                    if index in page_values:
                        capital_table_fields = \
                            len(page_values[index])
                    else:
                        break
        parser_obj.paidup_capital_details = [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.paidup_capital_details])]


    def get_proper_index(self, index, default_index, possible_deltas, page_values):
        temp_index = [round(index - delta, 2) for delta in possible_deltas if round(index - delta, 2) in page_values]
        if temp_index:
            index = temp_index[0]
        else:
            index = round(index - default_index, 2)
        return index

    def populate_officers_and_representatives(self, parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text.split("\n") for t in list_of_t]
            values = [x for v in values for x in v]
            if 'Officers/Authorised Representative(s)' in values:
                index = self.get_proper_index(key, 74.34, [98, 74.37], page_values)
                if index in page_values:
                    charge_table_fields = \
                        len(page_values[index])
                else:
                    charge_table_fields = 0

                while(charge_table_fields == 5 or charge_table_fields == 2):
                    officer_details = page_values[index]
                    officer_details.sort(key=lambda x:x.x)
                    if index in page_values:
                        officers_dict = {
                            'name': '',
                            'officer_id': '',
                            'nationality': '',
                            'source_of_address': '',
                            'date_of_appointment': '',
                            'address': '',
                            'position': ''
                        }
                        if parser_obj.pending_officers_table is None:
                            officers_dict['name'] = officer_details[0].text
                            officers_dict['officer_id'] = officer_details[1].text
                            officers_dict['nationality'] = officer_details[2].text
                            officers_dict['source_of_address'] = officer_details[3].text
                            date_of_appointment_str = officer_details[4].text
                            officers_dict['date_of_appointment'] = datetime.strptime(date_of_appointment_str, '%d/%m/%Y') if date_of_appointment_str else None
                            index = self.get_proper_index(index, 25, [35], page_values)

                        if parser_obj.pending_officers_table is not None:
                            officers_dict = parser_obj.pending_officers_table
                            parser_obj.pending_officers_table = None
                        elif index not in page_values:
                            parser_obj.pending_officers_table = officers_dict
                            break

                        officers_dict['address'] = page_values[index][0].text
                        officers_dict['position'] = page_values[index][1].text
                        index = self.get_proper_index(index, 36, [49, 37, 49, 51, 47, 60, 62, 39], page_values)
                        parser_obj.officers_details.append(officers_dict)

                    if index in page_values:
                        charge_table_fields = len(page_values[index])
                    else:
                        break

    """
    Finds index in a string containing company records
    """
    def find_index(self,parser_obj,input_text,input_list):
        input_index = input_list.index(input_text)
        if input_index:
            return 0
        else:
            return 1


    """
    Populates records in company records table
    """
    def populate_company_record_table(self, parser_obj, page_values):
        temp_page_values = {k: v for k,v in page_values.iteritems() if v}

        for key, list_of_t in temp_page_values.iteritems():
            values = [t.text for t in list_of_t]
            # #Print statements for debug
            # print key, "\t", value, "\t"

            if ':' in values:
                values.remove(':')

            if (len(values) == 1):
                values.append('')

            for v in values:
                bizfile_date = re.match('^Date:.\d+/\d+/\d+', v if type(v) == str or type(v) == unicode else v.text)
                if bizfile_date:
                    bizfile_date_str = bizfile_date.group(0).split(':')[1].strip()
                    parser_obj.company_record['bizfile_date'] = datetime.strptime(bizfile_date_str, '%d/%m/%Y') if bizfile_date_str else None

            if 'Registration No.' in values:
                index = self.find_index(parser_obj,'Registration No.',values)
                parser_obj.company_record['registration_no'] = values[index].replace(':', '').strip()
            elif 'Company Name.' in values:
                index = self.find_index(parser_obj,'Company Name.',values)
                parser_obj.company_record['company_name'] = values[index].replace(':', '').strip()
            elif 'Former Name if any' in values:
                index = self.find_index(parser_obj,'Former Name if any',values)
                parser_obj.company_record['former_name'] = values[index].replace(':', '').strip()
            elif 'Incorporation Date.' in values:
                incorp_date_str = values[self.find_index(parser_obj,'Incorporation Date.',values)].replace(':', '').strip()
                parser_obj.company_record['incorp_date'] = datetime.strptime(incorp_date_str, '%d/%m/%Y') if incorp_date_str else None
            elif 'Company Type' in values:
                index = self.find_index(parser_obj,'Company Type',values)
                parser_obj.company_record['company_type'] = values[index].replace(':', '').strip()
            elif 'Status' in values:
                index = self.find_index(parser_obj,'Status',values)
                parser_obj.company_record['status'] = values[index].replace(':', '').strip()
            elif 'Status Date' in values:
                index = self.find_index(parser_obj,'Status Date',values)
                status_date_str = values[index].replace(':', '').strip()
                parser_obj.company_record['status_date'] = datetime.strptime(status_date_str, '%d/%m/%Y') if status_date_str else None
            elif 'Activities (I)' in values:
                activities_1 = page_values[round(key - 4, 2)][0].text if page_values[round(key - 4, 2)] else ''
                parser_obj.company_record['activities_1'] = activities_1
            elif 'Activities (II)' in values:
                activities_2 = page_values[round(key - 4, 2)][0].text if page_values[round(key - 4, 2)] else ''
                parser_obj.company_record['activities_2'] = activities_2
            elif 'Description' in values:
                activities_desc = page_values[round(key - 4, 2)][0].text if page_values[round(key - 4, 2)] else ''
                if round(key + 24, 2) in page_values and activities_desc:
                    parser_obj.company_record['activites_description'] = activities_desc
                elif activities_desc:
                    parser_obj.company_record['activites_description_2'] = activities_desc

            elif 'Registered Office Address' in values:
                registered_office_address = page_values[round(key - 4, 2)][0].text if page_values[round(key - 4, 2)] else ''
                parser_obj.company_record['registered_office_address'] = registered_office_address
            elif 'Date of Address' in values:
                date_of_address_str = page_values[round(key - 4, 2)][0].text if page_values[round(key - 4, 2)] else ''
                date_of_address = datetime.strptime(date_of_address_str, '%d/%m/%Y') if date_of_address_str else None
                parser_obj.company_record['date_of_address'] = date_of_address
            elif 'Date of Last AGM' in values:
                index = self.find_index(parser_obj,'Date of Last AGM',values)
                date_of_last_agm_str = values[index].replace(':', '').strip()
                parser_obj.company_record['date_of_last_agm'] = datetime.strptime(date_of_last_agm_str, '%d/%m/%Y') if date_of_last_agm_str else None
            elif 'Date of Last AR' in values:
                date_of_last_ar_str = values[self.find_index(parser_obj,'Date of Last AR',values)].replace(':', '').strip()
                parser_obj.company_record['date_of_last_ar'] = datetime.strptime(date_of_last_ar_str, '%d/%m/%Y') if date_of_last_ar_str else None
            elif 'Date of A/C Laid at Last AGM' in values:
                date_of_ac_at_last_str = values[self.find_index(parser_obj,'Date of A/C Laid at Last AGM',values)].replace(':', '').strip()
                parser_obj.company_record['date_of_ac_at_last'] = datetime.strptime(date_of_ac_at_last_str, '%d/%m/%Y') if date_of_ac_at_last_str else None
            elif 'Date of Lodgment of AR, A/C' in values:
                date_of_lodgment_of_ar_str = values[self.find_index(parser_obj,'Date of Lodgment of AR, A/C',values)].replace(':', '').strip()
                parser_obj.company_record['date_of_lodgment_of_ar'] = datetime.strptime(date_of_lodgment_of_ar_str, '%d/%m/%Y') if date_of_lodgment_of_ar_str else None
            elif 'RECEIPT NO.' in values:
                receipt_no = page_values[round(key + 1, 2)][0].text if page_values[round(key + 1, 2)] else ''
                parser_obj.company_record['receipt_no'] = receipt_no
            elif 'Audit Firms' in values:
                audit_index = round(key - 51.34, 2)
                if audit_index in page_values:
                    parser_obj.company_record['audit_firm_name'] = page_values[audit_index][0].text



    def _build_annotations( self, page):
        for annot in page.annots.resolve():
            if isinstance( annot, PDFObjRef ):
                annot= annot.resolve()
                assert annot['Type'].name == "Annot", repr(annot)
                if annot['Subtype'].name == "Widget":
                    if annot['FT'].name == "Btn":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V'].name
                    elif annot['FT'].name == "Tx":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V']
                    elif annot['FT'].name == "Ch":
                        assert annot['T'] not in self.fields
                        self.fields[ annot['T'] ] = annot['V']
                        # Alternative choices in annot['Opt'] )
                    else:
                        raise Exception( "Unknown Widget" )
            else:
                raise Exception( "Unknown Annotation" )

def run_pdf_parser():
    parser_object = PdfParser(conf)
    provider_object = PdfParserProvider()
    provider_object.load_pdf_file(parser_object)

    print "\n ##### Company details ###### \n"
    for key, value in parser_object.company_record.iteritems():
        print key, "\t", value

    print "\n\nCHARGES TABLE DETAILS"
    print len(parser_object.charges)
    for charge_value in parser_object.charges:
        print charge_value

    print "\n\nCAPITAL TABLE DETAILS\n"
    print len(parser_object.capital_details)
    for capital_value in parser_object.capital_details:
        print capital_value

    print "\n\nPAID-UP CAPITAL TABLE DETAILS\n"
    print len(parser_object.paidup_capital_details)
    for paidup_capital in parser_object.paidup_capital_details:
        print paidup_capital

    print "\n\nSHAREHOLDERS TABLE DETAILS\n"
    print len(parser_object.shareholders_details)
    for shareholder_value in parser_object.shareholders_details:
        print shareholder_value
        print "\n"

    print "\n\nSHAREHOLDER TYPE TABLE DETAILS\n"
    print len(parser_object.shareholder_type_details)
    for shareholder_type_value in parser_object.shareholder_type_details:
        print shareholder_type_value
        print "\n"

    print "\n\nOFFICERS TABLE DETAILS\n"
    print len(parser_object.officers_details)
    for officer_detail in parser_object.officers_details:
        print officer_detail
        print "\n"

if __name__ == "__main__":
    run_pdf_parser()

