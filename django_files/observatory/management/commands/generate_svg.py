# stdlib
import urllib2
from subprocess import Popen
import os
import time
import httplib
# graphics
#import cairo
#import rsvg
# django
from django.core.management.base import BaseCommand, CommandError
from django.utils.translation import get_language_info
from django.conf import settings
# App specific
from observatory.models import *

# Setup the path constants 

# Setup the supported languages so that we can loop over them
supported_langs = (
	(get_language_info('en'), 'usa'),
	#(get_language_info('es'), 'esp'),
	#(get_language_info('tr'), 'tur'),
	#(get_language_info('ja'), 'jpn'),
	#(get_language_info('it'), 'ita'),
	#(get_language_info('de'), 'deu'),
	#(get_language_info('el'), 'grc'),
	#(get_language_info('fr'), 'fra'),
	#(get_language_info('he'), 'isr'),
	#(get_language_info('ar'), 'sau'),
	#(get_language_info('zh-cn'), 'chn'),
	#(get_language_info('ru'), 'rus'),
	#(get_language_info('nl'), 'nld'),
	#(get_language_info('pt'), 'prt'),
	#(get_language_info('hi'), 'ind'),
	#(get_language_info('ko'), 'kor'), 
	)
	
# Setup the supported trade_flow so that we can loop over them
trade_flow_list = ["export", "import", "net_export", "net_import" ]

#Setup the supported trade_flow so that we can loop over them
#app_name = ["treemap", "product_space", "stacked", "pie_scatter" ]
class Command( BaseCommand ):
    help = 'Generate the JSON & SVG data for all permutations of the data set'

    def handle(self, *args, **options):
        # Setup the product classifications -> years mapping
        product_classifications = { "Sitc4": [ 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010], #Sitc4_cpy.objects.values_list( "year", flat=True ).distinct().order_by( '-year' ), 
                                    "Hs4": [2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011] }#Hs4_cpy.objects.values_list( "year", flat=True ).distinct().order_by( '-year' ) }

        # Get the different "Product Classifications" and loop over them
        for p_classification, p_classification_years in product_classifications.items():
            # Debug
            self.stdout.write( "Handling Product Classification: %s" % ( p_classification ) )
            self.stdout.write( "\n" )

            # Loop over the available years
            for p_classification_year in p_classification_years:
                # Debug
                self.stdout.write( "Handling Year: %s" % p_classification_year )
                self.stdout.write( "\n" )

                # Get a list of all the countries and loop over them
                #countries = Country.objects.values()
                countries = [ { 'name_3char': "ind" } ]
                # Loop over the countries
                for country in countries:
                    # Loop through all the languages available
                    for language in supported_langs:
                        # Loop through all the trade_flow available
                        for trade_flow in trade_flow_list:
                            # Build the API JSON Data URL
                            api_url = "http://127.0.0.1:8080/api/" + trade_flow + "/" + country['name_3char'].lower() + "/all/show/" + str( p_classification_year ) + "/?lang=" + language[0]['code'].replace( '-', '_' ) + "&data_type=json&prod_class=" + p_classification.lower()

                            # Setup the page url
                            page_url = "http://127.0.0.1:8080/explore/stacked/" + trade_flow + "/" + country['name_3char'].lower() + "/all/show/" + str( p_classification_year ) + "/?lang=" + language[0]['code'].replace( '-', '_' ) + "&prod_class=" + p_classification.lower() + "&headless=true"
                            
                            # Debug
                            self.stdout.write( 'Processing API Request URL --> "%s"' % api_url )
                            self.stdout.write( "\n" )
                            
                            # Setup the file name
                            file_name ="stacked" + "_" + language[0]['code'] + "_" + p_classification.lower() + "_" + trade_flow + "_" + country['name_3char'].lower() + "_all_show_" + str( p_classification_year )
                            
                            # We only want to do the below for data that doesn't already exist
                            if ( os.path.exists( settings.DATA_FILES_PATH + "/" + file_name + ".svg" ) is False ):
                                # Call the save_json and let it handle it at this point
                                return_code = self.save_json( api_url, file_name + ".json" )
                                
                                # Check the return code before proceeding
                                if ( return_code is True ):
                                    # Call the generate SVG method
                                    self.save_svg( page_url, file_name + ".svg" )
                                    
                                    # Call the generate PNG method
                                    self.save_png( file_name )
                                    
                                    # Let us now remove the json file since we don't want it anymore
                                    os.remove( settings.DATA_FILES_PATH + "/" + file_name + ".json" )
                                
                                # We should wait for a bit before the next one
                                time.sleep( 10 )
                            else:
                                # We have already generated the data for this permutation
                                self.stdout.write( 'Data already exists. Skipping ...' )
                                self.stdout.write( "\n" )
                            
                            # Let us break after one for now
                            #import sys
                            #sys.exit( 0 )
                            
    def save_json( self, api_url, file_name ):
        # Wrap everything in a try block
        try:
            # Let us setup the request
            json_request = urllib2.urlopen( api_url )
            
            # get the data from the request
            json_data = json_request.read()
	        
	        # Now we want to write this to file
            json_file = open( settings.DATA_FILES_PATH + "/" + file_name, "w+" )
            json_file.write( json_data )
            json_file.close()
            
            # Set the return code to True
            return True
        except urllib2.URLError, exc:
            # We seem to have run in to problems, degrade gracefully
            self.stdout.write( "There was an URLLIB Error processing the HTTP request ..." )
            self.stdout.write( "\n" )
            print exc
        except httplib.HTTPException, exc:
            # We seem to have run in to problems, degrade gracefully
            self.stdout.write( "There was an HTTP Error processing the HTTP request ..." )
            self.stdout.write( "\n" )
            print exc
        except IOError, exc:
            # We seem to have run in to problems, degrade gracefully
            self.stdout.write( "There was an IO Error processing the HTTP request ..." )
            self.stdout.write( "\n" )
            print exc
            
        # Return false at this point, since we should not come here
        return False
        
    def save_svg( self, page_url, file_name ):
        # Let us setup the phantomjs script arguments
        phantom_arguments = [ settings.PHANTOM_JS_EXECUTABLE, settings.PHANTOM_JS_SCRIPT, settings.DATA_FILES_PATH + "/" + file_name, page_url ]
        
        # Debug
        self.stdout.write( "Calling PhantomJS -->" )
        self.stdout.write( "\n" )
        print phantom_arguments
        
        # Let us setup the request
        phantom_execute = Popen( phantom_arguments )
        
        # Get the output data from the phantomjs execution
        execution_results = phantom_execute.communicate()
        
        # Print the stdout data
        print execution_results[0]
        
        # Wait until the SVG file is actually generated
        while ( os.path.exists( settings.DATA_FILES_PATH + "/" + file_name ) != True ):
            # Sleep for a bit and then continue with the loop
            time.sleep( 10 )
            
    def save_png( self, file_name ):
        try:
            import cairo, rsvg
        except:
            pass

        import rsvg
        import cairo  
        # Get the SVG data
        svg_file = open( settings.DATA_FILES_PATH + "/" + file_name + ".svg", "r" )
        svg_data = svg_file.read()
        # Create the blank image surface
        img = cairo.ImageSurface( cairo.FORMAT_ARGB32, 750, 480 )

        # Get the context
        ctx = cairo.Context( img )

        # Dump SVG data to the image context
        handler = rsvg.Handle( None, str( svg_data ) )
        handler.render_cairo( ctx )

        # Create the final png image
        final_png = img.write_to_png( settings.DATA_FILES_PATH + "/" + file_name + ".png" )
