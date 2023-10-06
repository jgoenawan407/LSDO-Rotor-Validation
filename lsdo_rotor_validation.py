# Jackson Goenawan, 10/6/23

import subprocess
import math
import matplotlib.pyplot as plt
import re
from csdl import Model
from lsdo_rotor.core.BEM.BEM_model import BEMModel

class BEMVerification:

	def __init__(self, xrotor_path, output_path, geo_desc): # Passing personalized file paths for subprocess and output parsing
		
		self.xrotor_path = xrotor_path
		self.output_path = output_path
		self.geo_desc = geo_desc

	# Replace a certain line in a text file with a given string
	def replace_line(self, file_name, line_num, text):

	    lines = open(file_name, 'r').readlines()
	    lines[line_num] = text
	    out = open(file_name, 'w')
	    out.writelines(lines)
	    out.close()

	# Return the line number in geometry file that contains RPM command
	def get_rpm_line(self, file_name):

		lines = open(file_name, 'r').readlines()
		# return ((int)(lines[5]) + 8)

		rpm_line = 0
		while lines[rpm_line].find("RPM") == -1:
			rpm_line += 1
		return rpm_line

	# Given our rotor parameters (flight speed) and prescribed RPM, return advanced ratio
	def get_adv_ratio(self, file_name):

		lines = open(file_name, 'r').readlines()
		velocity = int(lines[2])
		radius = float(lines[3])
		rpm = int(lines[self.get_rpm_line(file_name)][4:])

		rps = rpm / 60.0
		j = velocity / (2 * radius * rps)
		return j

	def get_thrust(self, file_name): # thrust coefficient C_t

		lines = open(file_name, 'r').readlines() # need results.txt as file
		
		# find the line that "Ct" is in
		thrust_line = 0
		found_thrust = False
		while found_thrust == False:
			thrust_line += 1
			if "Ct:" in lines[thrust_line][3 : 6]:
				found_thrust = True
			# exits the loop while i is the index of the line containing "thrust"

		thrust = float(lines[thrust_line][10 : 17]) # turns sci. notation into decimal form
		return thrust

	def get_Cp(self, file_name):

		lines = open(file_name, 'r').readlines() # need results.txt as file
		
		# find the line that "Cp" is in
		cp_line = 0
		while lines[cp_line].find("Cp:") == -1: # returns -1 if string doesn't contain "Cp:"
			cp_line += 1

		# find where "Cp:" is in cp_line --> gather the Cp value
		cp_pos = lines[cp_line].find("Cp:")
		cp = float(lines[cp_line][cp_pos + 7 : cp_pos + 14])
		return cp

	def get_kQ(self, file_name):

		lines = open(file_name, 'r').readlines() # need results.txt as file

		# find total torque
		torque_line = 0
		while lines[torque_line].find("torque") == -1: # returns -1 if string doesn't contain "torque"
			torque_line += 1
		start = lines[torque_line].find("torque") # position of the first letter in "torque(N-m):"
		full_torque_desc = lines[torque_line][start:]
		m_Q = re.search(r"\d", full_torque_desc)
		q = float(full_torque_desc[m_Q.start() :])

		# kq = Q / (\rho * n^2 * D^5)

		# find rho
		rho_line = 0
		print(rho_line)
		while lines[rho_line].find("rho") == -1: # returns -1 if string doesn't contain "rho"
			rho_line += 1
		print(rho_line)
		m1 = re.search(r"\d", lines[rho_line]) # first digit in the rho line is the "3" in units desc
		rho_line_substring = lines[rho_line][m1.start() + 1 :] # find first digit of actual rho
		m2 = re.search(r"\d", rho_line_substring)
		rho = float(rho_line_substring[m2.start() : m2.start() + 7])

		# find n (rps), must use results file, NOT geo_desc since we pass results file through
		rpm_line = 0
		while lines[rpm_line].find("rpm") == -1:
			rpm_line += 1
		rpm_start = lines[rpm_line].find("rpm")
		full_rpm = lines[rpm_line][rpm_start : ] # "rpm: " + actual rpm measurement
		m_rpm = re.search(r"\d", full_rpm)
		rps = float(full_rpm[m_rpm.start() :]) / 60

		# find diameter
		radius_line_1 = 0 # first 2 lines w "radius" is shell command, need to find third instance
		while lines[radius_line_1].find("radius") == -1:
			radius_line_1 += 1
		radius_line_2 = radius_line_1 + 1
		while lines[radius_line_2].find("radius") == -1:
			radius_line_2 += 1
		radius_line_3 = radius_line_2 + 1
		while lines[radius_line_3].find("radius") == -1:
			radius_line_3 += 1
		radius_start = lines[radius_line_3].find("radius")
		radius_line_substring = lines[radius_line_3][radius_start : ] # "rpm: " + actual rpm measurement
		m_radius = re.search(r"\d", radius_line_substring)
		diameter = 2 * float(radius_line_substring[m_radius.start() : m_radius.start() + 6])

		kQ = q / ((rho * math.pow(rps, 2) * math.pow(diameter, 5)))
		return kQ

	# Search for eta in our results file, add eta & adv. ratio to their respective arrays
	def add_etaJ_point(self, ratio, ratios, effs):
		
		lines = open(self.output_path, 'r').readlines()
		eff_string = "Efficiency : "

		# Read through file lines until we see "Efficiency :  "
		reached_eff = False
		i = -1
		while reached_eff == False:
			i = i + 1
			if eff_string in lines[i]:
				reached_eff = True

		# i gives us the line at which efficiency is found, so now we can store eta
		eff_line = lines[i]
		eta = float(lines[i][len(eff_string) + 1: len(eff_string) + 6])

		# Add eta and J to our arrays
		ratios.append(ratio)
		effs.append(eta)

	def graph_eta_vs_J(self, max_speed, max_rpm, min_rpm, rpm_step):

		# Arrays containing coordinate components for our efficiency vs. J plot
		ratios = []
		effs = []
		file_directive = self.xrotor_path + " < " + self.geo_desc

		# Loop through a range of flight speeds so that we can compare efficiencies between propellers with different adv. ratios
		for i in range(1, max_speed):

			# Replace the flight speed in our file with the next speed in sequence
			new_speed = str(i) + "\n"
			self.replace_line(self.geo_desc, 2, new_speed)
			print(str(i))

			# Open text file that will store our Free Tip Potential Formulation Solution
			results = open(self.output_path, "w")

			# Feed .ARBI commands into XROTOR and flush output into results.txt
			subprocess.call(file_directive, shell = True, stdout = results)

			# Add J and eta value for this propeller into their respective arrays
			self.add_etaJ_point(self.get_adv_ratio(self.geo_desc), ratios, effs)

		# Decrease RPM and iterate through lower RPMs to get highers J's
		for j in range(max_rpm, min_rpm, rpm_step):

			new_rpm = "RPM " + str(j) + "\n"
			self.replace_line(self.geo_desc, self.get_rpm_line(self.geo_desc), new_rpm)
			print(str(j))
			results = open(self.output_path, "w")
			subprocess.call(file_directive, shell = True, stdout = results)
			self.add_etaJ_point(self.get_adv_ratio(self.geo_desc), ratios, effs)

		# Plot list of eff's against list of adv. ratios
		plt.xlabel("Advance Ratio")
		plt.ylabel("Efficiency")
		plt.plot(ratios, effs, marker = 'o')
		plt.show()

	def graph_thrust_vs_J(self, max_speed, max_rpm, min_rpm, rpm_step):
		
		# Arrays containing coordinate components for our thrust vs. J plot
		ratios = []
		thrusts = []
		file_directive = self.xrotor_path + " < " + self.geo_desc

		for i in range(1, max_speed):

			# Replace the flight speed in our file with the next speed in sequence
			new_speed = str(i) + "\n"
			self.replace_line(self.geo_desc, 2, new_speed)
			print(str(i))

			# Open text file that will store our Free Tip Potential Formulation Solution
			results = open(self.output_path, "w")

			# Feed .ARBI commands into XROTOR and flush output into results.txt
			subprocess.call(file_directive, shell = True, stdout = results)

			# Add J and thrust value for this propeller into their respective arrays
			ratios.append(self.get_adv_ratio(self.geo_desc))
			thrusts.append(self.get_thrust(self.output_path))

		# Decrease RPM and iterate through lower RPMs to get highers J's
		for j in range(max_rpm, min_rpm, rpm_step):

			new_rpm = "RPM " + str(j) + "\n"
			self.replace_line(self.geo_desc, self.get_rpm_line(self.geo_desc), new_rpm)
			print(str(j))
			results = open(self.output_path, "w")
			subprocess.call(file_directive, shell = True, stdout = results)
			ratios.append(self.get_adv_ratio(self.geo_desc))
			thrusts.append(self.get_thrust(self.output_path))

		# Plot list of eff's against list of adv. ratios
		plt.xlabel("Advance Ratio")
		plt.ylabel("Thrust Coefficient (C_T)")
		plt.plot(ratios, thrusts, marker = 'o')
		plt.show()

	def graph_Cp_vs_J(self, max_speed, max_rpm, min_rpm, rpm_step):

		# Arrays containing coordinate components for our power vs. J plot
		ratios = []
		powers = []
		file_directive = self.xrotor_path + " < " + self.geo_desc

		for i in range(1, max_speed):

			# Replace the flight speed in our file with the next speed in sequence
			new_speed = str(i) + "\n"
			self.replace_line(self.geo_desc, 2, new_speed)
			print(str(i))

			# Open text file that will store our Free Tip Potential Formulation Solution
			results = open(self.output_path, "w")

			# Feed .ARBI commands into XROTOR and flush output into results.txt
			subprocess.call(file_directive, shell = True, stdout = results)

			# Add J and thrust value for this propeller into their respective arrays
			ratios.append(self.get_adv_ratio(self.geo_desc))
			powers.append(self.get_Cp(self.output_path))

		# Decrease RPM and iterate through lower RPMs to get highers J's
		for j in range(max_rpm, min_rpm, rpm_step):

			new_rpm = "RPM " + str(j) + "\n"
			self.replace_line(self.geo_desc, self.get_rpm_line(self.geo_desc), new_rpm)
			print(str(j))
			results = open(self.output_path, "w")
			subprocess.call(file_directive, shell = True, stdout = results)
			ratios.append(self.get_adv_ratio(self.geo_desc))
			powers.append(self.get_Cp(self.output_path))

		# Plot list of eff's against list of adv. ratios
		plt.xlabel("Advance Ratio")
		plt.ylabel("Power Coefficient (C_p)")
		plt.plot(ratios, powers, marker = 'o')
		plt.show()

	def graph_kQ_vs_J(self, max_speed, max_rpm, min_rpm, rpm_step):
		# Arrays containing coordinate components for our torque vs. J plot
		ratios = []
		torques = []
		file_directive = self.xrotor_path + " < " + self.geo_desc

		for i in range(1, max_speed):

			# Replace the flight speed in our file with the next speed in sequence
			new_speed = str(i) + "\n"
			self.replace_line(self.geo_desc, 2, new_speed)
			print(str(i))

			# Open text file that will store our Free Tip Potential Formulation Solution
			results = open(self.output_path, "w")

			# Feed .ARBI commands into XROTOR and flush output into results.txt
			subprocess.call(file_directive, shell = True, stdout = results)

			# Add kQ and thrust value for this propeller into their respective arrays
			ratios.append(self.get_adv_ratio(self.geo_desc))
			torques.append(self.get_kQ(self.output_path))

		# Decrease RPM and iterate through lower RPMs to get highers J's
		for j in range(max_rpm, min_rpm, rpm_step):

			new_rpm = "RPM " + str(j) + "\n"
			self.replace_line(self.geo_desc, self.get_rpm_line(self.geo_desc), new_rpm)
			print(str(j))
			results = open(self.output_path, "w")
			subprocess.call(file_directive, shell = True, stdout = results)
			ratios.append(self.get_adv_ratio(self.geo_desc))
			torques.append(self.get_kQ(self.output_path))

		# Plot list of eff's against list of adv. ratios
		plt.xlabel("Advance Ratio")
		plt.ylabel("Torque Coefficient (k_Q)")
		plt.plot(ratios, torques, marker = 'o')
		plt.show()

	def graph_cL_vs_r(self, file_name):

		lines = open(self.output_path, 'r').readlines()
		radii = []
		lifts = []

		# find where the radial dist table starts
		beta_line = 0
		while lines[beta_line].find("beta") == -1:
			beta_line = beta_line + 1
		
		i = beta_line + 1
		while lines[i] != "\n": # go until the end of the table
			
			radii.append(float(lines[i][4:9]))
			lifts.append(float(lines[i][25:30]))
			i = i + 1

		plt.xlabel("Normalized Radius")
		plt.ylabel("Lift Coefficient (C_L)")
		plt.plot(radii, lifts, marker = 'o')
		plt.show()

	def plot_geo_dist(self, geo_desc): # Plot normalized chord and twist angle against normalized radius

		lines = open(geo_desc, 'r').readlines()

		# find the line when we start describing the chord distribution
		reached_profile = False
		i = -1
		while reached_profile == False: # profile description is the first place when line length exceeds 4 characters
			i = i + 1
			if len(lines[i]) > 5:

				reached_profile = True
				profile_start_index = i

		# find the line when we stop describing the chord distribution
		reached_profile_end = False
		i = profile_start_index
		while reached_profile_end == False:
			i = i + 1
			if len(lines[i]) < 5:
				reached_profile_end = True
				last_profile_index = i - 1

		normalized_rads = []
		normalized_chords = []
		angles = []

		# add each float to its corresponding array (we'll have 3 floats per line)
		for j in range(profile_start_index, last_profile_index + 1):
			
			current_line = lines[j]
			normalized_rads.append(float(current_line.partition(" ")[0])) # substring until we reach the first space
			norm_chord_and_angle = current_line.partition(" ")[2]
			normalized_chords.append(float(norm_chord_and_angle.partition(" ")[0])) # take the middle third of our line
			angles.append(float(norm_chord_and_angle.partition(" ")[2]))
		
		plt.plot(normalized_rads, normalized_chords, marker = 'o')
		plt.xlabel("r/R")
		plt.ylabel("c/R")
		plt.show()
		plt.plot(normalized_rads, angles, marker = "s")
		plt.xlabel("r/R")
		plt.ylabel("Twist angle")
		plt.show()

def main():

	# Set paths for XROTOR .exe file, a text file for XROTOR output, and your geometric parameters text file --> create a BEMVerification object

if __name__ == "__main__":
    main()