#!/usr/bin/env python
#Standard imports
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

DEFAULTS = {"input_pdf_file": "testcases/inputfile1.pdf",
            }

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
                'date_uploaded': '',
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
        self.pending_officers_table = None
        self.pending_shareholders_table = None

        self.charges = []
        self.capital_details = []
        self.paidup_capital_details = []
        self.shareholders_details = []
        self.officers_details = []

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
        laparams = LAParams(detect_vertical=True, all_texts=True, line_margin=0.2)
      
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
                        charges_dict['date_registered'] = page_values[index][1]
                        charges_dict['amount_secured'] = page_values[index][2]
                        charges_dict['charge_org'] = page_values[index][3]
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

    """
    Populate the table containing shareholders object
    """
    def populate_shareholders_table(self, parser_obj, page_values):
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            if 'Shareholder(s)' in values:
                for k , list_of_t in page_values.iteritems():
                    print k, list_of_t
                    print '\n'
                # import ipdb;ipdb.set_trace()
                index = self.get_index(key, 74.34, [97.34], page_values)
                records_id = 0
                #To check if the Charges table is empty
                if index in page_values:
                    shareholders_table_fields = \
                        len(page_values[index])
                else:
                    shareholders_table_fields = 0

                while(shareholders_table_fields in [5, 1, 2]):
                    if index in page_values:
                        shareholders_dict = {'id':'',
                                            'name':'',
                                            'address':'',
                                            'shareholder_id':'',
                                            'nationality':'',''
                                            'source_of_address':'',
                                            'address_changed':'',
                                            'currency':'',
                                            'odinary_num':'',
                                            'company_record':''}

                        if parser_obj.pending_shareholders_table is None:
                            try:
                                shareholders_dict['id'] = page_values[index][2].text
                            except:
                                break
                                # import ipdb;ipdb.set_trace()
                            shareholders_dict['name'] = page_values[index][1].text
                            shareholders_dict['nationality'] = page_values[index][3].text
                            shareholders_dict['source_of_address'] = page_values[index][4].text
                            index = round(index-27.0, 2)

                        if not index in page_values:
                            index = round(index  - 10, 2)

                        if parser_obj.pending_shareholders_table is not None:
                            shareholders_dict = parser_obj.pending_shareholders_table
                            parser_obj.pending_shareholders_table = None
                        elif index not in page_values:
                            parser_obj.pending_shareholders_table = shareholders_dict
                            parser_obj.shareholders_details.append(shareholders_dict)
                            break

                        if (index in page_values):
                            shareholders_table_fields = len(page_values[index])
                            if (shareholders_table_fields == 1):
                                shareholders_dict['address'] = page_values[index][0].text

                        index = self.get_index(index, 81, [70, 58], page_values)

                        if (index in page_values):
                            shareholders_table_fields = len(page_values[index])
                            if(shareholders_table_fields == 2):
                                shareholders_dict['ordinary_num'] = page_values[index][0].text
                                shareholders_dict['currency'] = page_values[index][1].text
                        else:
                            parser_obj.pending_shareholders_table = shareholders_dict
                            parser_obj.shareholders_details.append(shareholders_dict)
                            break

                        parser_obj.shareholders_details.append(shareholders_dict)
                        records_id = records_id + 1
                        index = round(index - 24, 2)

                    if index in page_values:
                        shareholders_table_fields = len(page_values[index])
                    else:
                        break
        parser_obj.shareholders_details = \
            [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.shareholders_details])]


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
                                        'capital_type':'',
                                        'amount':'',
                                        'shares':'',
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['shares'] = page_values[index][0].text
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
                                        'capital_type':'',
                                        'amount':'',
                                        'shares':'',
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['currency'] = page_values[index][1].text
                        capital_dict['share_type'] = page_values[index][2].text
                        capital_dict['shares'] = ''
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
                    if index in page_values:
                        officers_dict = {
                            'name': '',
                            'id': '',
                            'nationality': '',
                            'source_of_address': '',
                            'date_of_appointment': '',
                            'address': '',
                            'position_held': ''
                        }
                        if parser_obj.pending_officers_table is None:
                            officers_dict['name'] = officer_details[0].text
                            officers_dict['id'] = officer_details[1].text
                            officers_dict['nationality'] = officer_details[2].text
                            officers_dict['source_of_address'] = officer_details[3].text
                            officers_dict['date_of_appointment'] = officer_details[4].text
                            index = self.get_proper_index(index, 25, [35], page_values)

                        if parser_obj.pending_officers_table is not None:
                            officers_dict = parser_obj.pending_officers_table
                            parser_obj.pending_officers_table = None
                        elif index not in page_values:
                            parser_obj.pending_officers_table = officers_dict
                            break

                        officers_dict['address'] = page_values[index][0].text
                        officers_dict['position_held'] = page_values[index][1].text
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
        for key, list_of_t in page_values.iteritems():
            values = [t.text for t in list_of_t]
            # #Print statements for debug
            # print key, "\t", value, "\t"

            if ':' in values:
                values.remove(':')

            if (len(values) == 1):
                values.append('')

            if 'Registration No.' in values:
                index = self.find_index(parser_obj,'Registration No.',values)
                parser_obj.company_record['registration_no'] = values[index]
            elif 'Company Name.' in values:
                index = self.find_index(parser_obj,'Company Name.',values)
                parser_obj.company_record['company_name'] = values[index]
            elif 'Former Name if any' in values:
                index = self.find_index(parser_obj,'Former Name if any',values)
                parser_obj.company_record['former_name'] = values[index]
            elif 'Incorporation Date.' in values:
                index = self.find_index(parser_obj,'Incorporation Date.',values)
                parser_obj.company_record['incorp_date'] = values[index]
            elif 'Company Type' in values:
                index = self.find_index(parser_obj,'Company Type',values)
                parser_obj.company_record['company_type'] = values[index]
            elif 'Status' in values:
                index = self.find_index(parser_obj,'Status',values)
                parser_obj.company_record['status'] = values[index]
            elif 'Status Date' in values:
                index = self.find_index(parser_obj,'Status Date',values)
                parser_obj.company_record['status_date'] = values[index]
            elif 'Activities (I)' in values:
                index = self.find_index(parser_obj,'Activities (I)',values)
                parser_obj.company_record['activities_1'] = values[index]
            elif 'Activities (II)' in values:
                index = self.find_index(parser_obj,'Activities (II)',values)
                parser_obj.company_record['activities_2'] = values[index]
            elif ('Description' in values) and (len(values)==1):
                parser_obj.company_record['activities_description'] = ''
            elif ('Description' in values) and (len(values)>1):
                index = self.find_index(parser_obj,'Description',values)
                parser_obj.company_record['activities_description'] = values[index]
            elif 'Registered Office Address' in values:
                index = self.find_index(parser_obj,'Registered Office Address',values)
                parser_obj.company_record['registered_office_address'] = values[index]
            elif 'Date of Address' in values:
                index = self.find_index(parser_obj,'Date of Address', values)
                parser_obj.company_record['date_of_address'] = values[index]
            elif 'Date of Last AGM' in values:
                index = self.find_index(parser_obj,'Date of Last AGM',values)
                parser_obj.company_record['date_of_last_agm'] = values[index]
            elif 'Date of Last AR' in values:
                index = self.find_index(parser_obj,'Date of Last AR',values)
                parser_obj.company_record['date_of_last_ar'] = values[index]
            elif 'Date of A/C Laid at Last AGM' in values:
                index = self.find_index(parser_obj,'Date of A/C Laid at Last AGM',values)
                parser_obj.company_record['date_of_ac_at_last'] = values[index]
            elif 'Date of Lodgment of AR, A/C' in values:
                index = self.find_index(parser_obj,'Date of Lodgment of AR, A/C',values)
                parser_obj.company_record['date_of_lodgment_of_ar'] = values[index]



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

    print "\n\nOFFICERS TABLE DETAILS\n"
    print len(parser_object.officers_details)
    for officer_detail in parser_object.officers_details:
        print officer_detail
        print "\n"

if __name__ == "__main__":
    run_pdf_parser()

