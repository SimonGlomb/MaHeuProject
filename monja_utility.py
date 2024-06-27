from datetime import timedelta

# find the earliest possible timeslots (and corresponding path) for a car
def assign_timeslots(car, paths, segments, eot):
    path = None
    departures = []
    earliest_arrival = None

    # for all potential paths, check the earliest arrival date -> pick the best one
    for i in range(len(car['paths'])):
        p = car['paths'][i]
        earliest_start = car['avlDate']
        current_timetable = []
        for j in range(len(paths[p])):
            potential_times = [s for s in segments[paths[p][j]]['timeslots'].keys() if s >= earliest_start and segments[paths[p][j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
            if len(potential_times) > 0:
                departure = min(potential_times)
            else: # path is blocked -> try the next path
                break
            current_timetable.append(departure)
            if j != len(paths[p])-1: # determine ealiest departure from current location
                earliest_start = (departure + timedelta(hours=segments[paths[p][j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
            else: # last segment: determine arrival time
                arrival = departure + timedelta(hours=segments[paths[p][j]]['duration'])
                if earliest_arrival == None or arrival < earliest_arrival:
                    earliest_arrival = arrival
                    departures = current_timetable
                    path = p
          
    if departures == []: # all paths are blocked, pretend that car arrives at the end of timeframe but assign no path
        return [], None, eot
    
    return departures, path, earliest_arrival

# find earliest route to a destination starting from an intermediate location
def earliest_timeslots_from_loc(car, paths, segments, start_loc, start_time, eot):
    departures = []
    earliest_arrival = None
    path = None # path used to complete the route
    index = None # index of the path-segment leaving the start location

    # check arrival times for all potential paths and pick the best one
    for i in range(len(car['paths'])):
        p = car['paths'][i]
        current_timetable = []
        earliest_start = start_time
        # check if path p contains start_loc, and if so, at which position
        stops = [segments[s]['start'] for s in paths[p]]
        if start_loc in stops:
            start_index = stops.index(start_loc)
        else: # if p does not contain start_loc, skip it
            break
        
        # traverse segments (starting in start location) and pick the earliest possible timeslots
        for j in range(len(paths[p][start_index:])):
            potential_times = [s for s in segments[paths[p][start_index + j]]['timeslots'].keys() if s >= earliest_start and segments[paths[p][start_index + j]]['timeslots'][s] > 0] # timeslots after the ealiest possible departure with open capacities
            if len(potential_times) > 0:
                departure = min(potential_times)
            else: # path is blocked -> continue with next path
                break
            current_timetable.append(departure)
            if j != len(paths[p][start_index:])-1: # compute earliest allowed departure time from current location
                earliest_start = (departure + timedelta(hours=segments[paths[p][start_index + j]]['duration']+24)).replace(hour=0, minute=0, second=0, microsecond=0)
            else: # last segment: determine arrival time
                arrival = departure + timedelta(hours=segments[paths[p][start_index + j]]['duration'])
                if earliest_arrival == None or arrival < earliest_arrival: # find earliest of the potential arrival times
                    earliest_arrival = arrival
                    departures = current_timetable
                    path = p
                    index = start_index
          
    if departures == []: # if all paths are blocked, pretend that car arrives at the end of timeframe
        return departures, None, None, eot
    
    return departures, path, index, earliest_arrival

