# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsVectorLayer,
                       QgsFillSymbol,
                       QgsProject,
                       QgsMarkerSymbol,
                       QgsLineSymbol,
                       QgsSingleSymbolRenderer,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink)
import processing


class ExampleProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT = 'INPUT'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return ExampleProcessingAlgorithm()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'myscript'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('My Script')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr('Example scripts')

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'examplescripts'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Example algorithm short description")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source. It can have any kind of
        # geometry.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input layer'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Output layer')
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """

        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(
            parameters,
            self.INPUT,
            context
        )

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))
       
        # Send some information to the user
        feedback.pushInfo('CRS is {}'.format(source.sourceCrs().authid()))

        import datetime
        import os
        
        start_t = datetime.datetime.now()

        chosen_file = self.parameterDefinition('INPUT').valueAsPythonString(parameters['INPUT'], context)
        source_path = os.path.dirname(chosen_file[1:]) + '/'
        #source_path = "E://GIS Programming/report project/Project_vector_file/"
        output_path = source_path+  "output_layer/"

        #Step 1: Clip some outline vector layers (Roads & POI)
        #Clip the Roads
        Clip_Roads = processing.run("native:clip", 
            {
                'INPUT':source_path + 'TR_ROAD_ALL.shp',
                'OVERLAY':source_path + 'EXTRACT_POLYGON.shp',
                'OUTPUT': output_path + 'Road_Clip.shp'
                }
        )

        #Clip the POI
        Clip_POI = processing.run("native:clip", 
            {
                'INPUT':source_path + 'POI_POINT.shp',
                'OVERLAY':source_path+ 'EXTRACT_POLYGON.shp',
                'OUTPUT':output_path + 'POI_Clip.shp'
                }
        )

        #Step 2: Buffer the bus station 
        Buffer = processing.run("native:buffer",
            {
                'INPUT':source_path + 'PTV_METRO_BUS_STOP.shp',
                'DISTANCE':200,
                'SEGMENTS':5,
                'END_CAP_STYLE':0,
                'JOIN_STYLE':0,
                'MITER_LIMIT':2,
                'DISSOLVE':True,
                'OUTPUT':output_path + 'Bus_Buffer.shp'
            }
        )

        #Step 3: Creat a service area of FOI in Sunshine West suburb
        Service = processing.run("native:serviceareafromlayer", 
            {
                'INPUT':output_path + 'Road_Clip.shp',
                'STRATEGY':0,
                'DIRECTION_FIELD':'',
                'VALUE_FORWARD':'',
                'VALUE_BACKWARD':'',
                'VALUE_BOTH':'',
                'DEFAULT_DIRECTION':2,
                'SPEED_FIELD':'',
                'DEFAULT_SPEED':50,
                'TOLERANCE':0,
                'START_POINTS':output_path + 'POI_Clip.shp',
                'TRAVEL_COST2':500,
                'INCLUDE_BOUNDS':True,
                'OUTPUT_LINES':output_path + 'POI_Service_area.shp'
            }
        )


        #Step 4: Convex the polygon of service area above
        Convex_hull = processing.run("native:convexhull", 
            {
                'INPUT':Service['OUTPUT_LINES'],
                'OUTPUT':output_path + 'Convex_hull_FOI.shp'
            }
        )

        #Step 5: open the vector layer into QGISe
        vlayer_EXTRACT_POLYGON = QgsVectorLayer(source_path + 'EXTRACT_POLYGON.shp', "EXTRACT_POLYGON", "ogr")
        vlayer_BUS_STOPS = QgsVectorLayer(source_path + 'PTV_METRO_BUS_STOP.shp', "BUS_STOPS", "ogr")
        vlayer_Road_Clip = QgsVectorLayer(output_path + 'Road_Clip.shp', "Road_Clip", "ogr")
        vlayer_POI_Clip = QgsVectorLayer(output_path + 'POI_Clip.shp', "POI_Clip", "ogr")
        vlayer_Bus_Stops_Buffer = QgsVectorLayer(output_path + 'Bus_Buffer.shp', "Bus_Stops_Buffer", "ogr")
        vlayer_POI_Service_area = QgsVectorLayer(output_path + 'POI_Service_area.shp', "POI_Service_area", "ogr")
        vlayer_Convex_hull_POI = QgsVectorLayer(output_path + 'Convex_hull_FOI.shp', 'Convex_hull_FOI', 'ogr')

        #Step 6: Symbolise the layers and show them on the map
        #Symbolise the vlayer_EXTRACT_POLYGON
        sym1 = QgsFillSymbol.createSimple({'color': '#ffffff', 'outline_color': '#ffe601'})
        renderer = QgsSingleSymbolRenderer(sym1)
        vlayer_EXTRACT_POLYGON.setRenderer(renderer)
        vlayer_EXTRACT_POLYGON.setOpacity(1)
        vlayer_EXTRACT_POLYGON.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_EXTRACT_POLYGON)

        #Symbolise the vlayer_BUS_STOPS
        symbol = QgsMarkerSymbol.createSimple({'color': '#49b359'})
        vlayer_BUS_STOPS.renderer().setSymbol(symbol)
        vlayer_BUS_STOPS.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_BUS_STOPS)

        #Symbolise the vlayer_Road_Clip
        symbol = QgsLineSymbol.createSimple({'line_style': 'solid', 'color': '#ffc171'})
        vlayer_Road_Clip.renderer().setSymbol(symbol)
        vlayer_Road_Clip.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_Road_Clip)

        #Symbolise the vlayer_POI_Clip
        symbol = QgsMarkerSymbol.createSimple({'color': 'black'})
        vlayer_POI_Clip.renderer().setSymbol(symbol)
        vlayer_POI_Clip.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_POI_Clip)

        #Symbolise the vlayer_Bus_Stops_Buffer
        sym1 = QgsFillSymbol.createSimple({'color': '#ba1e3b', 'outline_color': 'black'})
        renderer = QgsSingleSymbolRenderer(sym1)
        vlayer_Bus_Stops_Buffer.setRenderer(renderer)
        vlayer_Bus_Stops_Buffer.setOpacity(0.5)
        vlayer_Bus_Stops_Buffer.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_Bus_Stops_Buffer)

        #Symbolise the vlayer_POI_Service_area
        symbol = QgsLineSymbol.createSimple({'line_style': 'solid', 'color': '#6cca00'})
        vlayer_POI_Service_area.renderer().setSymbol(symbol)
        vlayer_POI_Service_area.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_POI_Service_area)

        #Symbolise the vlayer_Convex_hull_POI
        sym1 = QgsFillSymbol.createSimple({'color': '#97a7ff', 'outline_color': 'black'})
        renderer = QgsSingleSymbolRenderer(sym1)
        vlayer_Convex_hull_POI.setRenderer(renderer)
        vlayer_Convex_hull_POI.setOpacity(0.4)
        vlayer_Convex_hull_POI.triggerRepaint()
        QgsProject.instance().addMapLayer(vlayer_Convex_hull_POI)

        #The timetacker
        end_t = datetime.datetime.now()

        elapsed_sec = (end_t - start_t).total_seconds()
        print("Wasting time: " + "{:.2f}".format(elapsed_sec) + " seconds")
        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        return {self.OUTPUT: True}
        
def flags(self):
        return QgsProcessingAlgorithm.FlagNoThreading
