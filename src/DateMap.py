from datetime import datetime as dt
import datetime
from dateutil.relativedelta import relativedelta

class DateMap :
    """
        Helper class to coarsen timegrid, for operations like compute monthly average
    """
    def __init__(self, start_time: str, time_unit : str, time_steps : int):
        self.time_unit = time_unit
        if time_unit == "months" :
            self.format_code = "%Y-%m"
        elif time_unit == "days" :
            self.format_code = "%Y-%m-%d"
        elif time_unit == "hours" : 
            self.format_code ="%Y-%m-%d %H"
        self.time_steps = time_steps
        self.start_time= dt.strptime(start_time, self.format_code) 
    def getTime(self, time_step : int):
        if(time_step > self.time_steps) : raise RuntimeError("[DateMap ERROR] time step out of range")
        time = {self.time_unit : time_step}
        
        return dt.strftime(self.start_time + relativedelta(**time), self.format_code)
    
    
    # def coarsen_time_grid(self, new_unit):
    #     print(f"[DateMap LOG] coarsening time from hours to {new_unit}")
    #     if(new_unit not in ["days", "months", "years"]):
    #         raise RuntimeWarning("[DateMap ERROR] The target coarsened unit needs to be one of days, months or years")
        
    #     steps = []
    #     current_step = 0
    #     current_time = self.start_time
    #     time = {new_unit : 1}
    #     while(current_step < self.time_steps) : 
    #         steps.append(current_step)
    #         next_time = current_time + relativedelta(**time)
    #         current_step += int((next_time - current_time).total_seconds() / 3600)
    #         current_time = next_time
    #     return steps

if __name__ == "__main__" :
    dm = DateMap("2026-2-9 00:00:00", 100000)
    # print(dm.getTime(0)+relativedelta(days = 1))
    print(dm.coarsen_time_grid("months"))
