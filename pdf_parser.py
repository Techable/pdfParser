#!/usr/bin/env python
#Standard imports
import logging
#Imports related to pdfminer
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument, PDFTextExtractionNotAllowed
from pdfminer.psparser import PSLiteral
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfdevice import PDFDevice
from pdfminer.pdftypes import PDFObjRef
from pdfminer.layout import LAParams, LTTextBoxHorizontal, LTTextBoxVertical
from pdfminer.converter import PDFPageAggregator
from collections import defaultdict, namedtuple

# default configuration dictionary which will be initialized when
# PdfParser objects are created

DEFAULTS = {"input_pdf_file": "testcases/inputfile6.pdf",
            }

# dictionary of configured values
conf = {}
TextBlock= namedtuple("TextBlock", ["x", "y", "text"])

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
        # Innitializing the input PDF file
        self.input_pdf_file = conf.get("input_pdf_file",  \
                              DEFAULTS["input_pdf_file"])

        self.horizontal_table = {}
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

        self.charges = []
        self.capital_details = []
        self.paidup_capital_details = []
        self.shareholders_details = []

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
        laparams = LAParams(detect_vertical=True, all_texts=True)
      
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
                self._build_annotations( page )
            page_text = self._get_text(parser_obj, pdf_aggregator_obj)
            parser_obj.page_number = page_num
            #TODO: Need to copy the data into parsed_output_text variable
            parser_obj.parsed_output_text[page_num + 1] = page_text
       
    """
    To fetch the text from the pdf_aggregator_obj
    """
    def _get_text(self, parser_obj, pdf_aggregator_obj):
        temporary_text = []
        layout = pdf_aggregator_obj.get_result()
        for layout_obj in layout:
            if isinstance( layout_obj, LTTextBoxHorizontal ):
                if layout_obj.get_text().strip():
                    layout_obj_y1 = round(((1000 * parser_obj.page_number) + \
                                    layout_obj.y1),2)
                    temporary_text.append( TextBlock(layout_obj.x0, \
                            layout_obj_y1, layout_obj.get_text().strip()) )
                    #TODO: Not the pythonic way to write the code
                    #Need to fix it
                    if layout_obj_y1 in parser_obj.horizontal_table.keys():
                        parser_obj.horizontal_table[layout_obj_y1].append( \
                                layout_obj.get_text().strip())
                    elif (layout_obj_y1 + 4) in parser_obj.horizontal_table.keys():
                        parser_obj.horizontal_table[layout_obj_y1 + 4].append( \
                                layout_obj.get_text().strip())
                    elif (layout_obj_y1 - 4) in parser_obj.horizontal_table.keys():
                        parser_obj.horizontal_table[layout_obj_y1 - 4].append( \
                                layout_obj.get_text().strip())
                    else:
                        parser_obj.horizontal_table[layout_obj_y1] = \
                        [layout_obj.get_text().strip()]

        #Appending the key value pairs in the dictionary
        self.populate_company_record_table(parser_obj)
        self.populate_charges_record_table(parser_obj)
        self.populate_share_capital_table(parser_obj)
        self.populate_paidup_capital_table(parser_obj)
        self.populate_shareholders_table(parser_obj)
        print temporary_text
        return temporary_text



    """
    Populate the table containing charges
    """
    def populate_charges_record_table(self, parser_obj):
        for key, value in parser_obj.horizontal_table.iteritems():
            if 'Charge No.' in value:
                index = round(key - 28.34, 2)
                records_id = 0
                #To check if the Charges table is empty
                if index in parser_obj.horizontal_table:
                    charge_table_fields = \
                        len(parser_obj.horizontal_table[index])
                else:
                    charge_table_fields = 0

                while(charge_table_fields == 4):
                    charge_ids = [charge['charge_no'] \
                        for charge in parser_obj.charges]
                    charge_no = parser_obj.horizontal_table[index][0]
                    if index in parser_obj.horizontal_table:

                        charges_dict = {'id':'',
                                        'charge_no':'',
                                        'date_registered':'',
                                        'currency':'',
                                        'amount_secured':'',
                                        'charge_org':''}

                        charges_dict['charge_no'] = charge_no
                        charges_dict['date_registered'] = \
                                parser_obj.horizontal_table[index][1]
                        charges_dict['amount_secured'] = \
                                parser_obj.horizontal_table[index][2]
                        charges_dict['charge_org'] = \
                                parser_obj.horizontal_table[index][3]
                        parser_obj.charges.append(charges_dict)
                        records_id = records_id + 1
                        index = round(index - 36, 2)
                    if index in parser_obj.horizontal_table:
                        charge_table_fields = \
                            len(parser_obj.horizontal_table[index])
                    else:
                        break

        # remove duplicates of charges
        parser_obj.charges = [dict(t) for t in set([tuple(d.items()) for d in parser_obj.charges])]

    """
    Populate the table containing shareholders object
    """
    def populate_shareholders_table(self,parser_obj):
        for key, value in parser_obj.horizontal_table.iteritems():
            if 'Shareholder(s)' in value:
                index = round((key-74.34),2)
                records_id = 0
                #To check if the Charges table is empty
                if index in parser_obj.horizontal_table:
                    shareholders_table_fields = \
                        len(parser_obj.horizontal_table[index])
                else:
                    shareholders_table_fields = 0

                while(shareholders_table_fields == 5):
                    shareholders_id = [shareholders['id'] \
                        for shareholders in parser_obj.shareholders_details]
                    shareholder_id = parser_obj.horizontal_table[index][2]
                    if index in parser_obj.horizontal_table:
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

                        shareholders_dict['id'] = shareholder_id
                        shareholders_dict['name'] = \
                                parser_obj.horizontal_table[index][1]
                        shareholders_dict['nationality'] = \
                                parser_obj.horizontal_table[index][3]
                        shareholders_dict['source_of_address'] = \
                                parser_obj.horizontal_table[index][4]

                        index = round(index -27.0, 2)
                        if not index in parser_obj.horizontal_table:
                            index = round(index - 10.0, 2)

                        if not index in parser_obj.horizontal_table:
                            index = round(index  - 10)
                        #shareholders_table_fields = \
                        #    len(parser_obj.horizontal_table[index])
                        if (index in parser_obj.horizontal_table):
                            shareholders_table_fields = \
                            len(parser_obj.horizontal_table[index])
                            if (shareholders_table_fields == 2):
                                shareholders_dict['address'] = \
                                    parser_obj.horizontal_table[index][0]

                        index = round((index-70.0),2)
                        if (index in parser_obj.horizontal_table):
                            shareholders_table_fields = \
                            len(parser_obj.horizontal_table[index])
                            if(shareholders_table_fields == 2):
                                shareholders_dict['ordinary_num'] = \
                                    parser_obj.horizontal_table[index][0]
                                shareholders_dict['currency'] = \
                                    parser_obj.horizontal_table[index][1]

                        parser_obj.shareholders_details.\
                            append(shareholders_dict)
                        records_id = records_id + 1
                        index = round(index - 2, 2)

                    if index in parser_obj.horizontal_table:
                        shareholders_table_fields = \
                            len(parser_obj.horizontal_table[index])
                    else:
                        break
        parser_obj.shareholders_details = \
            [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.shareholders_details])]


    """
    Populate the Capital Details table
    """
    def populate_share_capital_table(self,parser_obj):
        for key, value in parser_obj.horizontal_table.iteritems():
            if 'Capital' in value:
                index = round((key-75.34),2)
                records_id = 0
                #To check if the Charges table is empty
                if index in parser_obj.horizontal_table:
                    capital_table_fields = \
                        len(parser_obj.horizontal_table[index])
                else:
                    capital_table_fields = 0

                while((capital_table_fields == 4) or \
                      (capital_table_fields == 3)):
                    capital_ids = [capital['amount'] \
                        for capital in parser_obj.capital_details]
                    amount = parser_obj.horizontal_table[index][0]
                    if index in parser_obj.horizontal_table:
                        capital_dict = {'id':'',
                                        'capital_type':'',
                                        'amount':'',
                                        'shares':'',
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['shares'] = \
                                parser_obj.horizontal_table[index][0]
                        capital_dict['currency'] = \
                                parser_obj.horizontal_table[index][1]
                        capital_dict['share_type'] = \
                                parser_obj.horizontal_table[index][2]
                        parser_obj.capital_details.append(capital_dict)
                        records_id = records_id + 1
                        index = round(index - 26, 2)
                    if index in parser_obj.horizontal_table:
                        capital_table_fields = \
                            len(parser_obj.horizontal_table[index])
                    else:
                        break
        parser_obj.capital_details = [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.capital_details])]

    """
    Populate the Paidup Capital Details table
    """
    def populate_paidup_capital_table(self,parser_obj):
        for key, value in parser_obj.horizontal_table.iteritems():
            if 'Paid-Up Capital' in value:
                index = round((key-50.34),2)
                records_id = 0
                #To check if the Charges table is empty
                if index in parser_obj.horizontal_table:
                    capital_table_fields = \
                        len(parser_obj.horizontal_table[index])
                else:
                    capital_table_fields = 0

                while(capital_table_fields == 3):
                    capital_ids = [capital['amount'] \
                        for capital in parser_obj.paidup_capital_details]
                    amount = parser_obj.horizontal_table[index][0]
                    if index in parser_obj.horizontal_table:
                        capital_dict = {'id':'',
                                        'capital_type':'',
                                        'amount':'',
                                        'shares':'',
                                        'currency':'',
                                        'share_type':''}

                        capital_dict['amount'] = amount
                        capital_dict['currency'] = \
                                parser_obj.horizontal_table[index][1]
                        capital_dict['share_type'] = \
                                parser_obj.horizontal_table[index][2]
                        capital_dict['shares'] = ''
                        parser_obj.paidup_capital_details.append(capital_dict)
                        records_id = records_id + 1
                        index = round(index - 36, 2)
                    if index in parser_obj.horizontal_table:
                        capital_table_fields = \
                            len(parser_obj.horizontal_table[index])
                    else:
                        break
        parser_obj.paidup_capital_details = [dict(t) for t in set([tuple(d.items()) \
            for d in parser_obj.paidup_capital_details])]


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
    def populate_company_record_table(self,parser_obj):
        for key, value in parser_obj.horizontal_table.iteritems():

            #Print statements for debug
            print key, "\t", value, "\t"

            if ':' in value:
                value.remove(':')

            if (len(value) == 1):
                value.append('')

            if 'Registration No.' in value:
                index = self.find_index(parser_obj,'Registration No.',value)
                parser_obj.company_record['registration_no'] = value[index]
            elif 'Company Name.' in value:
                index = self.find_index(parser_obj,'Company Name.',value)
                parser_obj.company_record['company_name'] = value[index]
            elif 'Former Name if any' in value:
                index = self.find_index(parser_obj,'Former Name if any',value)
                parser_obj.company_record['former_name'] = value[index]
            elif 'Incorporation Date.' in value:
                index = self.find_index(parser_obj,'Incorporation Date.',value)
                parser_obj.company_record['incorp_date'] = value[index]
            elif 'Company Type' in value:
                index = self.find_index(parser_obj,'Company Type',value)
                parser_obj.company_record['company_type'] = value[index]
            elif 'Status' in value:
                index = self.find_index(parser_obj,'Status',value)
                parser_obj.company_record['status'] = value[index]
            elif 'Status Date' in value:
                index = self.find_index(parser_obj,'Status Date',value)
                parser_obj.company_record['status_date'] = value[index]
            elif 'Activities (I)' in value:
                index = self.find_index(parser_obj,'Activities (I)',value)
                parser_obj.company_record['activities_1'] = value[index]
            elif 'Activities (II)' in value:
                index = self.find_index(parser_obj,'Activities (II)',value)
                parser_obj.company_record['activities_2'] = value[index]
            elif ('Description' in value) and (len(value)==1):
                parser_obj.company_record['activities_description'] = ''
            elif ('Description' in value) and (len(value)>1):
                index = self.find_index(parser_obj,'Description',value)
                parser_obj.company_record['activities_description'] = value[index]
            elif 'Registered Office Address' in value:
                index = self.find_index(parser_obj,'Registered Office Address',value)
                parser_obj.company_record['registered_office_address'] = value[index]
            elif 'Date of Address' in value:
                index = self.find_index(parser_obj,'Date of Address', value)
                parser_obj.company_record['date_of_address'] = value[index]
            elif 'Date of Last AGM' in value:
                index = self.find_index(parser_obj,'Date of Last AGM',value)
                parser_obj.company_record['date_of_last_agm'] = value[index]
            elif 'Date of Last AR' in value:
                index = self.find_index(parser_obj,'Date of Last AR',value)
                parser_obj.company_record['date_of_last_ar'] = value[index]
            elif 'Date of A/C Laid at Last AGM' in value:
                index = self.find_index(parser_obj,'Date of A/C Laid at Last AGM',value)
                parser_obj.company_record['date_of_ac_at_last'] = value[index]
            elif 'Date of Lodgment of AR, A/C' in value:
                index = self.find_index(parser_obj,'Date of Lodgment of AR, A/C',value)
                parser_obj.company_record['date_of_lodgment_of_ar'] = value[index]



    def _build_annotations( self, parser_obj, page ):
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
    #for i in parser_object.parsed_output_text:
    #	print parser_object.parsed_output_text.values()
    for key, value in parser_object.company_record.iteritems():
        print key, "\t", value
    print "\n\nCHARGES TABLE DETAILS"
    for charge_value in parser_object.charges:
        print charge_value
    print "\n\nCAPITAL TABLE DETAILS\n"
    for capital_value in parser_object.capital_details:
        print capital_value

    print "\n\nPAID-UP CAPITAL TABLE DETAILS\n"
    for paidup_capital in parser_object.paidup_capital_details:
        print paidup_capital

    print "\n\nSHAREHOLDERS TABLE DETAILS\n"
    for shareholder_value in parser_object.shareholders_details:
        print shareholder_value

    #for key, value in parser_object.charges.iteritems()
    #    print key, "\t", value
if __name__ == "__main__":
    run_pdf_parser()

