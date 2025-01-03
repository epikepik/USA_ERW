from typing import Dict, Tuple, Any
import pickle
import numpy as np
import netCDF4 as nc

# https://github.com/epikepik/USA_ERW
# e.kantzas@sheffield.ac.uk
class PaperData:

    def __init__(self, scen_id: int = 2, unc_id: int = 2,
                 flx_name: str = 'CO2', data_dir: str = None, output_dir: str = None):
        # The flux name
        self.flx_name = flx_name
        # The scenario id. Either 1 or 2.
        self.scen_id = scen_id
        # The uncertainty id. 1 for lower limit, 2 for mean, 3 for upper limit
        self.unc_id = unc_id
        if not data_dir:
            self.data_dir = '../data/'
        if not output_dir:
            self.output_dir = '../netcdf_outputs/'

    def main(self):
        """
        Main function. Will create netCDF file for the instanced variables
        :return: None
        """
        # Get empty arrays to fill
        # Will hold flux
        map_arr = self.get_zero_map_array(annual=True)
        # Will hold area
        map_arr_area = self.get_zero_map_array(annual=False)

        # Read data dic of the flux
        dic = self.load_from_pickl_var()

        # For each point
        for kk in dic:
            # Get ilat/ilon for the map
            ilat, ilon = dic[kk]['ind'][0], dic[kk]['ind'][1]
            # Get the dataframe
            df = dic[kk]['{}_a_b'.format(self.flx_name)]
            # Get the values to add in the array for the scenario and uncertainty
            val = df['S{}_U1_N{}_p100'.format(self.scen_id, self.unc_id)].to_numpy()
            # If not pH, P or K, just add the flux to the grid cell
            if self.flx_name not in ['pH', 'P_mass', 'K_mass']:
                # Add flux values to array
                map_arr[ilat, ilon, :] = map_arr[ilat, ilon, :] + val * self.get_flx_sign()
            else:
                # If pH, P or K you need to weight the value by the area
                # Add value to array but multiply by area first
                map_arr[ilat, ilon, :] = map_arr[ilat, ilon, :] + val * dic[kk]['ar']
                # Add area to array
                map_arr_area[ilat, ilon] = map_arr_area[ilat, ilon] + dic[kk]['ar']
        # Average for area
        if self.flx_name in ['pH', 'K_mass', 'P_mass']:
            with np.errstate(invalid='ignore', divide='ignore'):
                map_arr = map_arr / map_arr_area[:, :, np.newaxis]

        # Save data to nc
        self.save_nc(map_arr)

        return

    def save_nc(self, map_arr: np.ndarray) -> None:
        """
        Save flux array to netCDF file
        :param map_arr: Array with flux to save
        :return: None
        """
        # File name to save
        filn = '{}_S{}_U1_N{}_p80100_v6.nc'.format(self.flx_name, self.scen_id, self.unc_id)
        # Get latitude and longitude vector
        lat_vec, lon_vec = self.get_lat_lon()
        # Create the netcdf file
        ncfile = nc.Dataset('{}{}'.format(self.output_dir, filn), mode='w', format='NETCDF4_CLASSIC')
        # latitude axis
        _ = ncfile.createDimension('lat', np.shape(map_arr)[0])
        # longitude axis
        _ = ncfile.createDimension('lon', np.shape(map_arr)[1])
        # time axis
        _ = ncfile.createDimension('time', None)

        # Create latitude, longitude and flux array
        latitude = ncfile.createVariable('lat', np.float32, ('lat',))
        longitude = ncfile.createVariable('lon', np.float32, ('lon',))
        array = ncfile.createVariable(self.flx_name, np.float32, ('lat', 'lon', 'time'))

        # Assign values to variables
        latitude[:] = lat_vec
        longitude[:] = lon_vec
        array[:, :, :] = map_arr

        ncfile.close()

    def get_lat_lon(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get vectors with latitude and longitude values from the landmask file
        :return: Latitude and longitude vectors
        """
        dat = nc.Dataset('{}{}'.format(self.data_dir, 'landmask_0.23x0.31.nc'))
        lat = np.ma.getdata(dat['lat'][:])
        lon = np.ma.getdata(dat['lon'][:])

        return lat, lon

    def get_flx_sign(self) -> float:
        """
        Return sign of the flux. For CO2 is negative as its sequestration. Anything
        with fertilizer release/cost is also negative as it shows replacement of actual use.
        :return:
        """
        if self.flx_name in ['CO2', 'feem_K', 'feem_P', 'feco_K', 'feco_P']:
            return -1.
        return 1.

    def get_zero_map_array(self, annual: bool) -> np.ndarray:
        """
        Returns zero array with native dimensions of CLM global output
        :param annual: Whether to add a 3rd dimension with years of the run
        :return: Array with dimensions [lat, lon, years] for annual=True or
        [lat, lon] otherwise
        """
        # Reads land mask file from CLM to get the right dimensions for the array
        dat = nc.Dataset('{}{}'.format(self.data_dir, 'landmask_0.23x0.31.nc'))

        # Create zero array based on land mask
        zero_arr = np.zeros_like(np.ma.getdata(dat['landmask'][:]))
        # If annual, add a 3rd dimension for years
        if annual:
            zero_arr = zero_arr[:, :, np.newaxis]
            zero_arr = np.tile(zero_arr, 51)

        return zero_arr

    def load_from_pickl_var(self) -> Dict[int, Dict[str, Any]]:
        """
        Load pickle file with variable data
        :return: Dictionary with keys the point id and value a dictionary with data
        """
        fnam = "{}compiled_run_{}_v6_varz.pkl".format(
            self.data_dir, self.flx_name + '_a_b')
        with open(fnam, 'rb') as f:
            dic = pickle.load(f)

        return dic


# https://github.com/epikepik/USA_ERW
# e.kantzas@sheffield.ac.uk
if __name__ == '__main__':
    PaperData(scen_id=1, unc_id=2, flx_name='CO2').main()
