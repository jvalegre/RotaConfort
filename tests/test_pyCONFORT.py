#!/usr/bin/env python

import os
import pytest
import pandas as pd
import subprocess

# saves the working directory
path = os.getcwd()
# decimal digits for comparing E
precision = 5

def calc_energy(file):
    energy = []
    f = open(file,"r")
    readlines = f.readlines()
    for i,line in enumerate(readlines):
        if readlines[i].find('>  <Energy>') > -1:
            energy.append(float(readlines[i+1].split()[0]))
    f.close()
    return energy

# tests for individual organic molecules and metal complexes
@pytest.mark.parametrize("folder, smiles, params_file, n_confs, prefilter_confs_rdkit, filter_confs_rdkit, E_confs, charge, dihedral, xTB_ANI1, only_check",
[
    # tests for conformer generation with RDKit, xTB and ANI1
    ('Organic_molecules', 'pentane.smi', 'params_test1.yaml', 240, 236, 0, [-5.27175,-4.44184,-3.84858,-1.57172], 0, False, False, False), # test sample = 'auto', auto_sample = 20
    ('Organic_molecules', 'pentane.smi', 'params_test2.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test sample = 20
    ('Organic_molecules', 'pentane.smi', 'params_test3.yaml', 20, 2, 13, [-5.27175, -4.44184, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test initial_energy_threshold = 1E-10
    ('Organic_molecules', 'pentane.smi', 'params_test4.yaml', 20, 10, 0, [-5.27175, -5.27175, -5.27175, -5.27175, -4.44184, -4.44184, -4.44184, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test energy_threshold = 1E-15
    ('Organic_molecules', 'pentane.smi', 'params_test5.yaml', 20, 10, 0, [-5.27175, -5.27175, -5.27175, -5.27175, -4.44184, -4.44184, -4.44184, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test rms_threshold = 1E-15
    ('Organic_molecules', 'pentane.smi', 'params_test6.yaml', 20, 2, 11, [-5.27175, -4.44184, -4.44184, -4.44184, -4.44184, -3.84858, -1.57172], 0, False, False, False),
    ('Organic_molecules', 'pentane.smi', 'params_test7.yaml', 60, 56, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test sample = 'auto', auto_sample = 5
    ('Organic_molecules', 'pentane.smi', 'params_test8.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, False), # test max_torsions = 1
    ('Organic_molecules', 'pentane.smi', 'params_test9.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, False), # test max_MolWt = 1
    ('Organic_molecules', 'pentane.smi', 'params_test10.yaml', 20, 16, 0, [2.52059, 3.68961, 4.94318, 6.51778], 0, False, False, False), # test ff = 'UFF'
    ('Organic_molecules', 'pentane.smi', 'params_test11.yaml', 20, 0, 8, [-5.26093, -4.41687, -4.39313, -4.10961, -3.93585, -2.95568, -2.43353, -2.03709, -1.51856, -1.45757, -0.22202, 0.46406], 0, False, False, False), # test opt_steps_RDKit = 40
    ('Organic_molecules', 'pentane.smi', 'params_test12.yaml', 20, 16, 0, [-5.27175,-4.44184,-3.84858,-1.57172], 0, False, True, False), # test xTB = True
    ('Organic_molecules', 'pentane.smi', 'params_test13.yaml', 20, 16, 0, [-5.27175,-4.44184,-3.84858,-1.57172], 0, False, True, False), # test ANI1ccx = True
    ('Organic_molecules', 'pentane.smi', 'params_test14.yaml', 20, 16, 0, [-5.27175, -4.44184], 0, False, False, False), # ewin = 1
    ('Organic_molecules', 'pentane.smi', 'params_test15.yaml', 36, 'nan', 4, [-5.27175,-4.44184,-3.84858,-1.57172], 0, True, False, False), # test dihedral scan
    ('Metal_complexes', 'Ir_hexacoord.smi', 'params_Ir_test1.yaml', 1440, 1434, 0, [1.53156, 1.55012, 1.5506, 1.55114, 1.55163, 1.57662], 1, False, False, False), # test single metal with genecp
    ('Metal_complexes', 'Ir_hexacoord.smi', 'params_Ir_test2.yaml', 1440, 'nan', 6, [1.53156, 1.55012, 1.5506, 1.55114, 1.55163, 1.57662], 1, True, False, False), # test with dihedral scan
    ('Metal_complexes', 'Ag_Au_complex.smi', 'params_Ag_Au_test1.yaml', 360, 352, 0, [10.45361, 11.58698, 20.01407, 20.66195, 20.7945, 22.27646, 23.33896, 23.39252], 0, False, False, False), # test 2 metals with genecp
    ('Metal_complexes', 'Ag_Au_complex_2.smi', 'params_Ag_Au_test1.yaml', 20, 0, 0, [37.95387, 41.58506, 41.8691, 42.4647, 42.84581, 46.75471, 48.4257, 48.67218, 49.49887, 51.41683, 52.68135, 53.25264, 54.42994, 54.5214, 56.52762, 59.4592, 59.75275, 61.4215, 63.41206, 69.54026], 1, False, False, False), # test 2 metals with genecp and charge
    ('Metal_complexes', 'Ag_Au_complex_2.smi', 'params_Ag_Au_test2.yaml', 240, 'nan', 146, [37.23573, 37.31335, 37.06652, 37.06652, 36.44513, 36.44513, 37.56838, 39.10735, 38.25121, 36.82544, 41.50126, 41.38454, 41.08851, 41.08851, 41.59332, 41.16353, 41.50126, 41.96199, 41.80216, 41.44176, 41.35143, 41.49496, 41.96199, 42.58329, 42.58329, 42.27756, 42.45762, 44.78602, 43.13758, 41.73488, 42.06945, 43.25449, 42.95388, 42.37207, 42.48821, 41.97963, 41.8759, 41.73962, 41.99177, 41.77047, 41.77047, 45.8679, 45.37942, 45.10063, 44.86002, 44.86002, 46.061, 47.5134, 45.55071, 45.26116, 48.35549, 48.25914, 48.01912, 48.01912, 49.13862, 48.54182, 48.35549, 48.42979, 48.35888, 48.06073, 47.82973, 47.82973, 48.91924, 48.42979, 49.32764, 49.20842, 48.54182, 48.93583, 49.7613, 49.32764, 50.52429, 50.41912, 50.1949, 50.1949, 51.46385, 50.91743, 50.52429, 52.28854, 52.14992, 51.86265, 51.86265, 52.51926, 52.01584, 52.28854, 52.24474, 51.34867, 50.93369, 50.70741, 50.70741, 51.40979, 51.11125, 51.11125, 54.11384, 54.00488, 53.74388, 53.74388, 54.26089, 53.82847, 54.11384, 53.94834, 53.86956, 53.64612, 53.58215, 53.94834, 55.98447, 55.87742, 55.65245, 55.61573, 55.76332, 55.98447, 55.95913, 57.18201, 57.03223, 56.99672, 56.99672, 60.17173, 57.38656, 57.15537, 54.28566, 54.19244, 53.97537, 54.1921, 54.11074, 54.28566, 58.92905, 58.82661, 58.53368, 58.29505, 58.29505, 58.70893, 58.70893, 60.54619, 58.31212, 58.16207, 58.059, 60.17173, 58.15211, 58.15211, 67.79518, 63.04568, 61.99054, 61.81456, 61.81456, 62.2454, 62.6222, 61.81395], 1, True, False, False), # test with dihedral scan
    ('Metal_complexes', 'Pd_squareplanar.smi', 'params_Pd_test1.yaml', 360, 349, 0, [8.97676, 9.01872, 9.10379, 9.15897, 9.16366, 9.17272, 9.18237, 9.19448, 9.22382, 9.26467, 9.43331], 0, False, False, False), # test squareplanar template with gen
    ('Metal_complexes', 'Pd_squareplanar.smi', 'params_Pd_test2.yaml', 48, 'nan', 6, [8.97676, 8.97676, 9.01872, 9.18237, 9.15897, 9.19448], 0, True, False, False), # test nodihedral
    ('Metal_complexes', 'Rh_squarepyramidal.smi', 'params_Rh_test1.yaml', 360, 111, 0, [6.14954, 6.15497, 6.20729, 6.3288, 6.35036, 6.35559, 6.35893, 6.52387, 6.56902], 0, False, False, False), # test squareplanar template with gen
    # tests that will check if the code crushes when using combinations of organic molecules and metal complexes
    ('Multiple', 'pentane_Pd_blank_lines.smi', 'params_comb_test1.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test pentane + Pd complex with blank lines
    ('Multiple', 'pentane_Pd.smi', 'params_comb_test2.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test pentane + Pd complex
    ('Multiple', 'pentane_Pd_template.smi', 'params_comb_test3.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test pentane + Pd complex with template
    ('Multiple', 'pentane_Ag_Au.smi', 'params_comb_test4.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test pentane + 2 metals
    ('Multiple', 'pentane_Pd.smi', 'params_comb_test5.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test pentane + Pd + dihedral
    # tests to check that gen and genecp work correctly
    ('Genecp', 'Pd_squareplanar.smi', 'params_genecp_test1.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test gen
    ('Genecp', 'Pd_squareplanar.smi', 'params_genecp_test2.yaml', 'nan', 'nan', 'nan', 'nan', 'nan', False, False, True), # test genecp
    # tests of input files with different formats
    ('Input_files', 'pentane.csv', 'params_format_test1.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test csv
    ('Input_files', 'pentane.cdx', 'params_format_test2.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test cdx
    ('Input_files', 'pentane.com', 'params_format_test3.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test com
    ('Input_files', 'pentane.gjf', 'params_format_test4.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test gjf
    ('Input_files', 'pentane.sdf', 'params_format_test5.yaml', 20, 16, 0, [-5.27175, -4.44184, -3.84858, -1.57172], 0, False, False, False), # test sdf
])

def test_confgen(folder, smiles, params_file, n_confs, prefilter_confs_rdkit, filter_confs_rdkit, E_confs, charge, dihedral, xTB_ANI1, only_check):
    # gets into the directory for testing SMILES
    os.chdir(path+'/'+folder+'/'+smiles.split('.')[0])

    # Conformer generation using different parameters. It creates a CSV file
    subprocess.run(['python', '-m', 'DBGEN', '--varfile', params_file])

    if not only_check:
    	# Retrieving the generated CSV file
    	df_output = pd.read_csv(smiles.split('.')[0]+'-Duplicates Data.csv')

    	file = params_file.split('.')[0]

    	# tests for RDKit
    	if not dihedral:
    		test_init_rdkit_confs = df_output['RDKIT-Initial-samples']
    		test_prefilter_rdkit_confs = df_output['RDKit-energy-duplicates']
    		test_filter_rdkit_confs = df_output['RDKit-RMSD-and-energy-duplicates']

    		assert str(n_confs) == str(test_init_rdkit_confs[0])
    		assert str(prefilter_confs_rdkit) == str(test_prefilter_rdkit_confs[0])
    		assert str(filter_confs_rdkit) == str(test_filter_rdkit_confs[0])

    	else:
    		test_init_rdkit_confs = df_output['RDKIT-Rotated-conformers']
    		test_unique_confs = df_output['RDKIT-Rotated-Unique-conformers']

    		# I use the filter_confs_rdkit variable to assert for unique confs in dihedral scan
    		assert str(n_confs) == str(test_init_rdkit_confs[0])
    		assert str(filter_confs_rdkit) == str(test_unique_confs[0])

    	# read the energies of the conformers
    	os.chdir(path+'/'+folder+'/'+smiles.split('.')[0]+'/RDKit_generated_SDF_files')

    	if not dihedral:
    		test_rdkit_E_confs = calc_energy(smiles.split('.')[0]+'_rdkit.sdf')
    	else:
    		test_rdkit_E_confs = calc_energy(smiles.split('.')[0]+'_rdkit_rotated.sdf')

    	# test for energies
    	try:
    		test_round_confs = [round(num, precision) for num in test_rdkit_E_confs]
    		round_confs = [round(num, precision) for num in E_confs]
    	except:
    		test_round_confs = 'nan'
    		round_confs = 'nan'

    	assert str(round_confs) == str(test_round_confs)

    	# tests charge
    	test_charge = df_output['Overall charge']

    	assert str(charge) == str(test_charge[0])

    # check that the COM files are generated correctly with gen and gen_ecp
    else:
        if params_file.find('_genecp_') > -1:
            os.chdir(path+'/'+folder+'/'+smiles.split('.')[0]+'/generated_gaussian_files/wb97xd-def2svp')
            file = 'Pd_squareplanar_conformer_1.com'
            # count the amount of times Pd 0 is repeated: for gen only 1, for gen_ecp 2
            count = 0
            f = open(file,"r")
            readlines = f.readlines()
            for i, line in enumerate(readlines):
                if line.find('Pd 0') > -1:
                    count += 1
            f.close()

            if params_file == 'params_genecp_test1.yaml': # for gen
                assert count == 1
            else: # for genecp
                assert count == 2


# MISSING CHECKS:
# experimental rules
# analysis
# sp files
