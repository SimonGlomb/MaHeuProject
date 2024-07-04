import pandas as pd
from datetime import datetime, timedelta
import parse_txt
from utility import assign_timeslots, compute_car_costs

# convert date-string into something to work with 
def handle_dates(date_str):
    if date_str == "-":
        return date_str
    else:
        return datetime.strptime(date_str, '%d/%m/%Y-%H:%M:%S')

# computes the last date of the viewed timeframe (latest arrival of a planned transport)
def end_of_timeframe(segments):
    # for each segments compute the arrivaltime for the latest timeslot -> maximum arrival time is the end of the timeframe
    arrivals = [max(segments[s]['timeslots'].keys()) + timedelta(hours=segments[s]['duration']) for s in segments.keys() if len(segments[s]['timeslots'].keys()) != 0]
    eot = max(arrivals)
    return eot

# computes all dates of the time frame (not just those given in "timeslots") and returns them as an ordered list
def get_all_dates(cars, segments):
    earliest = min([cars[i]['avlDate'] for i in cars.keys()]) # earliest avl date of a car
    latest = end_of_timeframe(segments) # latest arrival of a transport
    dates = []
    current = earliest
    while current <= latest:
        dates.append(current)
        current += timedelta(days=1.0)
    return dates

# compute a very simple lower bound on the costs induced by the given car
def simple_lower_bound(car, paths, segments, eot):
    # determine earliest possible delivery date
    earliest_arrival = assign_timeslots(car, paths, segments, eot)[2]
    return compute_car_costs(car['avlDate'], car['dueDate'], earliest_arrival, car['deliveryRef'])

# compute upper bound for the costs induced by a single car
def simple_upper_bound(car, end_timeframe):
    # costs if tha rar arrives at the last dat of the timeframe
    return compute_car_costs(car['avlDate'], car['dueDate'], end_timeframe, car['deliveryRef'])

# transform the data from the dataframes of the file input into more intuitive structures
# only keep the relevant information and precompute some relevant values
def construct_instance(dataframes):
    cars={}
    paths={}
    segments={}

    car_df = dataframes['TRO']
    path_df = dataframes['PTH']
    pthseg_df = dataframes['PTHSG']
    segment_df = dataframes['SEG']
    departures_df = dataframes['PTR']

    # extract paths
    for i in path_df.index:
        id = path_df['ID(long)'][i]
        path = [] # corresponding path segments in the correct order
        path_segments = pthseg_df[pthseg_df['PathID(long)'] == id].sort_values('SegmentSequenceNumber')
        for j in path_segments.index:
            code = path_segments['SegmentCode'][j]
            sid = segment_df[segment_df['Code'] == code]['ID(long)'].iloc[0]
            path.append(sid)
        paths[id] = path

    # extract path-segments
    for i in segment_df.index:
        id = segment_df['ID(long)'][i]
        code = segment_df['Code'][i]
        segment = {'duration':float(segment_df['DefaultLeadTimeHours'][i]), 'start':segment_df['OriginCode'][i] , 'end':segment_df['DestinationCode'][i], 'name':code}
        timeslots = {}
        capacities = {}
        departures = departures_df[departures_df['PathSegmentCode'] == code]
        for j in departures.index:
            date_string = departures['TimeSlotDate'][j]
            key = handle_dates(date_string)
            timeslots[key] = float(departures['Capacity'][j]) # here the remaining capacity is tracked
            capacities[key] = float(departures['Capacity'][j]) # here the total capacity ist stored for reference

        segment['timeslots'] = timeslots
        segment['capacities'] = capacities
        segments[id] = segment

    # determine end of timeframe
    eot = end_of_timeframe(segments)

    # extract cars
    for i in car_df.index:
        id = car_df['ID(long)'][i]
        car = {'avlDate':handle_dates(car_df['AvailableDateOrigin'][i]), 
             'dueDate':handle_dates(car_df['DueDateDestinaton'][i])}
        
        # find possible paths for the car
        start = car_df['OriginCode'][i]
        car['origin'] = start
        end = car_df['DestinationCode'][i]
        car['destination'] = end
        filtered_paths = path_df[(path_df['PathOriginCode'] == start) & (path_df['PathDestinationCode'] == end)]
        pths=[]
        for j in filtered_paths.index:
            pths.append(filtered_paths['ID(long)'][j])
        car['paths'] = pths

        # compute the net transport time (hours)
        earliest_arrival = assign_timeslots(car, paths, segments, eot)[2]
        ref = (earliest_arrival - car['avlDate']).total_seconds()/(60*60)
        car['deliveryRef'] = ref

        # lower bound for the costs
        car['costBound'] = simple_lower_bound(car, paths, segments, eot)

        # set remaining values to empty values (they are set during the algorithm)
        car['assignedPath'] = None
        car['currentDelivery'] = None
        car['schedule'] = []
        car['inducedCosts'] = None

        cars[id] = car

    return cars, paths, segments, eot

# ids of cars, for which it is impossible to be delivered in the given network
def undeliverable(cars, paths, segments, eot):
    return [id for id in cars.keys() if assign_timeslots(cars[id], paths, segments, eot)[1] == None]

# ids of cars that cannot be on time
def always_late(cars, paths, segments, eot):
    return [id for id in cars.keys() if cars[id]['dueDate'] != "-" and assign_timeslots(cars[id], paths, segments, eot)[2] > cars[id]['dueDate']]








# instances = ["1","2a","2b","2c","3","4","5a","5b","6a","6b","6c","6d","6e","6f","6g",]
# for i in range(len(instances)):
#     df=parse_txt.parse_file(f"data\inst00{instances[i]}.txt")
#     a,b,c,d = construct_instance(df)
