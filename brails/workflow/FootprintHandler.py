# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 The Regents of the University of California
#
# This file is part of BRAILS.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# You should have received a copy of the BSD 3-Clause License along with
# BRAILS. If not, see <http://www.opensource.org/licenses/>.
#
# Contributors:
# Barbaros Cetiner
#
# Last updated:
# 05-12-2022  

import requests
import sys
import json
from itertools import groupby

class FootprintHandler:
    def __init__(self): 
        self.footprints = []
        self.queryarea = []
        
    def fetch_footprint_data(self,queryarea):
        """
        Function that loads footprint data from OpenStreetMap
        
        Input: Location entry defined as a string or a list of strings 
               containing the area name(s) or a tuple containing the longitude
               and longitude pairs for the bounding box of the area of interest
        Output: Footprint information parsed as a list of lists with each
                coordinate described in longitude and latitude pairs   
        """
        def get_osm_footprints(queryarea):
            if isinstance(queryarea,str):
                # Search for the query area using Nominatim API:
                print(f"\nSearching for {queryarea}...")
                queryarea = queryarea.replace(" ", "+").replace(',','+')
                
                queryarea_formatted = ""
                for i, j in groupby(queryarea):
                    if i=='+':
                        queryarea_formatted += i
                    else:
                        queryarea_formatted += ''.join(list(j))
                
                nominatimquery = ('https://nominatim.openstreetmap.org/search?' +
                                  f"q={queryarea_formatted}&format=json")
                
                r = requests.get(nominatimquery)
                datalist = r.json()
                
                areafound = False
                for data in datalist:
                    queryarea_turboid = data['osm_id'] + 3600000000
                    queryarea_name = data['display_name']
                    if(data['osm_type']=='relation' and 
                       'university' in queryarea.lower() and
                       data['type']=='university'):
                        areafound = True
                        break
                    elif (data['osm_type']=='relation' and 
                         data['type']=='administrative'): 
                        areafound = True
                        break
                
                if areafound==True:
                    print(f"Found {queryarea_name}")
                else:
                    sys.exit(f"Could not locate an area named {queryarea}. " + 
                             'Please check your location query to make sure' +
                             'it was entered correctly.')
                    
                        
            elif isinstance(queryarea,tuple):
                pass
            else:
                sys.exit('Incorrect location entry. The location entry must be defined' + 
                         ' as a string or a list of strings containing the area name(s)' + 
                         ' or a tuple containing the longitude and latitude pairs for' +
                         ' the bounding box of the area of interest.')
                         
                         
            
            # Obtain and parse the footprint data for the determined area using Overpass API:
            if isinstance(queryarea,str):
                queryarea_printname = queryarea_name.split(",")[0]
            elif isinstance(queryarea,tuple):
                queryarea_printname = (f"the bounding box: [{queryarea[0]}," 
                                       f"{queryarea[1]}, {queryarea[2]}, "
                                       f"{queryarea[3]}]")
            
            print(f"\nFetching footprint data for {queryarea_printname}...")
            url = 'http://overpass-api.de/api/interpreter'
            
            if isinstance(queryarea,str):
                query = f"""
                [out:json][timeout:5000];
                area({queryarea_turboid})->.searchArea;
                way["building"](area.searchArea);
                out body;
                >;
                out skel qt;
                """
            elif isinstance(queryarea,tuple):
                bbox = [min(queryarea[1],queryarea[3]),
                        min(queryarea[0],queryarea[2]),
                        max(queryarea[1],queryarea[3]),
                        max(queryarea[0],queryarea[2])]
                query = f"""
                [out:json][timeout:5000];
                way["building"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
                out body;
                >;
                out skel qt;
                """
                
            r = requests.get(url, params={'data': query})
            
            datalist = r.json()['elements']
            nodedict = {}
            for data in datalist:
                if data['type']=='node':
                   nodedict[data['id']] = [data['lon'],data['lat']]
        
        
            footprints = []
            for data in datalist:
                if data['type']=='way':
                    nodes = data['nodes']
                    footprint = []
                    for node in nodes:
                        footprint.append(nodedict[node])
                    footprints.append(footprint)
            
            print(f"Found a total of {len(footprints)} building footprints in {queryarea_printname}")
            return footprints

        def polygon_area(lats, lons):
        
            radius = 20925721.784777 # Earth's radius in feet
            
            from numpy import arctan2, cos, sin, sqrt, pi, append, diff, deg2rad
            lats = deg2rad(lats)
            lons = deg2rad(lons)
        
            # Line integral based on Green's Theorem, assumes spherical Earth
        
            #close polygon
            if lats[0]!=lats[-1]:
                lats = append(lats, lats[0])
                lons = append(lons, lons[0])
        
            #colatitudes relative to (0,0)
            a = sin(lats/2)**2 + cos(lats)* sin(lons/2)**2
            colat = 2*arctan2( sqrt(a), sqrt(1-a) )
        
            #azimuths relative to (0,0)
            az = arctan2(cos(lats) * sin(lons), sin(lats)) % (2*pi)
        
            # Calculate diffs
            # daz = diff(az) % (2*pi)
            daz = diff(az)
            daz = (daz + pi) % (2 * pi) - pi
        
            deltas=diff(colat)/2
            colat=colat[0:-1]+deltas
        
            # Perform integral
            integrands = (1-cos(colat)) * daz
        
            # Integrate 
            area = abs(sum(integrands))/(4*pi)
        
            area = min(area,1-area)
            if radius is not None: #return in units of radius
                return area * 4*pi*radius**2
            else: #return in ratio of sphere total area
                return area
        
        def load_footprint_data(fpfile):
            """
            Function that loads footprint data from a GeoJSON file
            
            Input: A GeoJSON file containing footprint information
            Output: Footprint information parsed as a list of lists with each
                    coordinate described in longitude and latitude pairs   
            """
            with open(fpfile) as f:
                data = json.load(f)['features']

            footprints = []
            for count, loc in enumerate(data):
                footprints.append(loc['geometry']['coordinates'][0][0])
            
            print(f"Found a total of {len(footprints)} building footprints in {fpfile}")
            return footprints

        self.queryarea = queryarea
        if isinstance(queryarea,str):
            if 'geojson' in queryarea.lower():
                self.footprints = load_footprint_data(queryarea)
            else:
                self.footprints = get_osm_footprints(queryarea)
        elif isinstance(queryarea,tuple):
            self.footprints = get_osm_footprints(queryarea)
        elif isinstance(queryarea,list):    
            self.footprints = []
            for query in queryarea: 
                self.footprints.extend(get_osm_footprints(query))
        else:
            sys.exit('Incorrect location entry. The location entry must be defined as' + 
                     ' 1) a string or a list of strings containing the name(s) of the query areas,' + 
                     ' 2) string containing the name of a GeoJSON file containing footprint data,' +
                     ' 3) or a tuple containing the coordinates for a rectangular' +
                     ' bounding box of interest in (lon1, lat1, lon2, lat2) format.' +
                     ' For defining a bounding box, longitude and latitude values' +
                     ' shall be entered for the vertex pairs of any of the two' +
                     ' diagonals of the rectangular bounding box.')   
             
        self.fpAreas = []
        for fp in self.footprints:
            lons = []
            lats = []
            for pt in fp:
                lons.append(pt[0])
                lats.append(pt[1])        
            self.fpAreas.append(polygon_area(lats, lons))