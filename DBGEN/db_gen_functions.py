#!/usr/bin/env python
"""##################################################.
# This file stores all the functions used by db_gen #
##################################################"""

import math, os, sys, subprocess, glob, shutil, time,yaml
from rdkit.Chem import AllChem as Chem
from rdkit.Chem import rdMolTransforms, PropertyMol, rdDistGeom, rdMolAlign, Lipinski, Descriptors
from rdkit.Geometry import Point3D
from progress.bar import IncrementalBar
import numpy as np
import pandas as pd

# imports for xTB and ANI1
try:
	import ase
	import ase.optimize
	from ase.units import Hartree
	import torch
	os.environ['KMP_DUPLICATE_LIB_OK']='True'
	device = torch.device('cpu')
except:
	print('0')
try:
	from lib.xtb import GFN2
except:
	print('1')
try:
	import torchani
	model = torchani.models.ANI1ccx()
except:
	print('5')

hartree_to_kcal = 627.509

possible_atoms = ["", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si",
				 "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
				 "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd",
				 "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm",
				 "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt",
				 "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu",
				 "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
				 "Rg", "Uub", "Uut", "Uuq", "Uup", "Uuh", "Uus", "Uuo"]
columns = ['Structure', 'E', 'ZPE', 'H', 'T.S', 'T.qh-S', 'G(T)', 'qh-G(T)']

# CLASS FOR LOGGING
class Logger:
	"""
	 Class Logger to write the output to a file
	"""
	def __init__(self, filein, append):
		"""
		Logger to write the output to a file
		"""
		suffix = 'dat'
		self.log = open('{0}_{1}.{2}'.format(filein, append, suffix), 'w')

	def write(self, message):
		print(message, end='\n')
		self.log.write(message+ "\n")

	def fatal(self, message):
		print(message, end='\n')
		self.log.write(message + "\n")
		self.finalize()
		sys.exit(1)

	def finalize(self):
		self.log.close()


def load_from_yaml(args,log):
	# Variables will be updated from YAML file
	if args.varfile != None:
		if os.path.exists(args.varfile):
			if os.path.splitext(args.varfile)[1] == '.yaml':
				log.write("\no  IMPORTING VARIABLES FROM " + args.varfile)
				with open(args.varfile, 'r') as file:
					param_list = yaml.load(file, Loader=yaml.FullLoader)

	for param in param_list:
		if hasattr(args, param):
			if getattr(args, param) != param_list[param]:
				log.write("o  RESET " + param + " from " + str(getattr(args, param)) + " to " + str(param_list[param]))
				setattr(args, param, param_list[param])
			else:
				log.write("o  DEFAULT " + param + " : " + str(getattr(args, param)))

def creation_of_dup_csv(args):
	# writing the list of DUPLICATES
	if args.nodihedrals:
		if args.xtb != True and args.ANI1ccx != True:
			dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','time (seconds)','Overall charge'])
		elif args.xtb:
			dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','xTB-Initial-samples','xTB-initial_energy_threshold','xTB-RMSD-and-energy-duplicates','xTB-Unique-conformers','time (seconds)','Overall charge'])
		elif args.ANI1ccx:
			dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','ANI1ccx-Initial-samples','ANI1ccx-initial_energy_threshold','ANI1ccx-RMSD-and-energy-duplicates','ANI1ccx-Unique-conformers','time (seconds)','Overall charge'])
	else:
		if args.xtb != True and args.ANI1ccx != True:
			dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','RDKIT-Rotated-conformers','RDKIT-Rotated-Unique-conformers','time (seconds)','Overall charge'])
		elif args.xtb:
			dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','RDKIT-Rotated-conformers','RDKIT-Rotated-Unique-conformers','xTB-Initial-samples','xTB-initial_energy_threshold','xTB-RMSD-and-energy-duplicates','xTB-Unique-conformers','time (seconds)','Overall charge'])
		elif args.ANI1ccx:
				dup_data =  pd.DataFrame(columns = ['Molecule','RDKIT-Initial-samples', 'RDKit-energy-duplicates','RDKit-RMSD-and-energy-duplicates','RDKIT-Unique-conformers','RDKIT-Rotated-conformers','RDKIT-Rotated-Unique-conformers','ANI1ccx-Initial-samples','ANI1ccx-initial_energy_threshold','ANI1ccx-RMSD-and-energy-duplicates','ANI1ccx-Unique-conformers','time (seconds)','Overall charge'])
	return dup_data

# SUBSTITUTION WITH I
def substituted_mol(smi,args,log):
	mol = Chem.MolFromSmiles(smi)
	for atom in mol.GetAtoms():
		if atom.GetSymbol() in args.metal:
			args.metal_sym.append(atom.GetSymbol() )
			atom.SetAtomicNum(53)
			if len(atom.GetNeighbors()) == 2:
				atom.SetFormalCharge(-3)
			if len(atom.GetNeighbors()) == 3:
				atom.SetFormalCharge(-2)
			if len(atom.GetNeighbors()) == 4:
				atom.SetFormalCharge(-1)
			if len(atom.GetNeighbors()) == 5:
				atom.SetFormalCharge(0)
			if len(atom.GetNeighbors()) == 6:
				atom.SetFormalCharge(1)
			if len(atom.GetNeighbors()) == 7:
				atom.SetFormalCharge(2)
			if len(atom.GetNeighbors()) == 8:
				atom.SetFormalCharge(3)
			args.metal_idx.append(atom.GetIdx())
			args.complex_coord.append(len(atom.GetNeighbors()))

	return mol,args.metal_idx,args.complex_coord,args.metal_sym

def clean_args(args,ori_ff,smi):
	mol = Chem.MolFromSmiles(smi)
	for atom in mol.GetAtoms():
		if atom.GetSymbol() in args.metal:
			args.metal_complex= True
			break
	else:
		args.metal_complex = False
	args.ff = ori_ff
	args.metal_idx = []
	args.complex_coord = []
	args.metal_sym = []

def compute_confs(smi, name,args,log,dup_data,counter_for_template,i,start_time):
	#taking largest component for salts
	pieces = smi.split('.')
	if len(pieces) > 1:
		# take largest component by length
		smi = max(pieces, key=len)

	# Converts each line to a rdkit mol object
	if args.verbose:
		log.write("   -> Input Molecule {} is {}".format(i, smi))

	if args.metal_complex:
		mol,args.metal_idx,args.complex_coord,args.metal_sym = substituted_mol(smi,args,log)
	else:
		mol = Chem.MolFromSmiles(smi)

	if args.metal_complex:
		# get manually for square planar and squarepyramidal
		if args.complex_type == 'squareplanar' or args.complex_type == 'squarepyramidal':
			mol_objects = []
			if len(args.metal_idx) == 1:
				file_template = os.path.dirname(os.path.abspath(__file__)) +'/template/template-4-and-5.sdf'
				temp = Chem.SDMolSupplier(file_template)
				mol_objects_from_template,name, coord_Map, alg_Map, mol_template = template_embed_sp(mol,temp,name,args,log)
				for i,_ in enumerate(mol_objects_from_template):
					mol_objects.append([mol_objects_from_template[i],name[i],coord_Map[i],alg_Map[i],mol_template[i]])
				for [mol, name, coord_Map,alg_Map,mol_template] in mol_objects:
					conformer_generation(mol,name,start_time,args,log,dup_data,counter_for_template,coord_Map,alg_Map,mol_template)
					counter_for_template += 1
			else:
				log.write("x  Cannot use templates for complexes involving more than 1 metal or for organic molecueles.")
		else:
			conformer_generation(mol,name,start_time,args,log,dup_data,i)
	else:
		conformer_generation(mol,name,start_time,args,log,dup_data,i)


# TEMPLATE GENERATION FOR SQUAREPLANAR AND squarepyramidal
def template_embed_sp(molecule,temp,name_input,args,log):
	mol_objects = [] # a list of mol objects that will be populated
	name_return = []
	coord_Map = []

	alg_Map = []
	mol_template = []

	for atom in molecule.GetAtoms():
		if atom.GetSymbol() == 'I'and (len(atom.GetBonds()) == 6 or len(atom.GetBonds()) == 5 or len(atom.GetBonds()) == 4 or len(atom.GetBonds()) == 3 or len(atom.GetBonds()) == 2):
			if len(atom.GetBonds()) == 5:
				atom.SetAtomicNum(15)
			if len(atom.GetBonds()) == 4:
				atom.SetAtomicNum(14)
			center_idx = atom.GetIdx()
			neighbours = atom.GetNeighbors()

	number_of_neighbours = len(neighbours)

	if number_of_neighbours == 4:
		#three cases for square planar
		for name in range(3):
			#assigning neighbours
			for atom in molecule.GetAtoms():
				if atom.GetIdx() == center_idx:
					neighbours = atom.GetNeighbors()

			#assigning order of replacement
			if name == 0:
				j = [1,2,3]
			elif name == 1:
				j = [2,3,1]
			elif name == 2:
				j = [3,1,2]

			#checking for same atom neighbours and assigning in the templates for all mols in suppl!
			for mol_1 in temp:
				for atom in mol_1.GetAtoms():
					if atom.GetSymbol() == 'F':
						mol_1 = Chem.RWMol(mol_1)
						idx = atom.GetIdx()
						mol_1.RemoveAtom(idx)
						mol_1 = mol_1.GetMol()

				site_1,site_2,site_3,site_4,metal_site  = 0,0,0,0,0
				for atom in mol_1.GetAtoms():
					if atom.GetIdx() == 4 and metal_site == 0:
						atom.SetAtomicNum(14)
						center_temp = atom.GetIdx()
						metal_site = 1
					if atom.GetIdx() == 0 and site_1 == 0:
						atom.SetAtomicNum(neighbours[0].GetAtomicNum())
						site_1 = 1
					if atom.GetIdx() == 3 and site_2 == 0:
						atom.SetAtomicNum(neighbours[j[0]].GetAtomicNum())
						site_2 = 1
					if atom.GetIdx() == 2 and site_3 == 0:
						atom.SetAtomicNum(neighbours[j[1]].GetAtomicNum())
						site_3 = 1
					if atom.GetIdx() == 1 and site_4 == 0 :
						atom.SetAtomicNum(neighbours[j[2]].GetAtomicNum())
						site_4 = 1

				#embedding of the molecule onto the core
				molecule_new, coordMap, algMap = template_embed_optimize(molecule,mol_1,args,log)

				for atom in molecule_new.GetAtoms():
					if atom.GetIdx() == center_idx:
						atom.SetAtomicNum(53)
						atom.SetFormalCharge(-1)

				for atom in mol_1.GetAtoms():
					if atom.GetIdx() == center_temp:
						atom.SetAtomicNum(53)
						atom.SetFormalCharge(-1)

				#writing to mol_object file
				name_final = name_input + str(name)
				mol_objects.append(molecule_new)
				name_return.append(name_final)
				coord_Map.append(coordMap)
				alg_Map.append(algMap)
				mol_template.append(mol_1)

	if number_of_neighbours == 5:
		#fifteen cases for square pyrimidal
		for name_1 in range(5):
			for name_2 in range(3):
				#assigning neighbours
				for atom in molecule.GetAtoms():
					if atom.GetIdx() == center_idx:
						neighbours = atom.GetNeighbors()

				for atom in neighbours:
					print(atom.GetSymbol(),atom.GetIdx())

				# assigning order of replacement for the top
				if name_1 == 0:
					k = 4
				elif name_1== 1:
					k = 3
				elif name_1 == 2:
					k = 2
				elif name_1== 3:
					k = 1
				elif name_1 == 4:
					k = 0

				# assigning order of replacement for the plane
				if name_2 == 0 and k == 4:
					j = [1,2,3]
				elif name_2 == 1 and k == 4:
					j = [2,3,1]
				elif name_2 == 2 and k == 4:
					j = [3,1,2]

				# assigning order of replacement for the plane
				if name_2 == 0 and k == 3:
					j = [1,2,4]
				elif name_2 == 1 and k == 3:
					j = [2,4,1]
				elif name_2 == 2 and k == 3:
					j = [4,1,2]

				# assigning order of replacement for the plane
				if name_2 == 0 and k == 2:
					j = [1,4,3]
				elif name_2 == 1 and k == 2:
					j = [4,3,1]
				elif name_2 == 2 and k == 2:
					j = [4,1,3]

				# assigning order of replacement for the plane
				if name_2 == 0 and k == 1:
					j = [4,2,3]
				elif name_2 == 1 and k == 1:
					j = [2,3,4]
				elif name_2 == 2 and k == 1:
					j = [3,4,2]

				# assigning order of replacement for the plane
				if name_2 == 0 and k == 0:
					j = [1,2,3]
				elif name_2 == 1 and k == 0:
					j = [2,3,1]
				elif name_2 == 2 and k == 0:
					j = [3,1,2]

				#checking for same atom neighbours and assigning in the templates for all mols in suppl!
				for mol_1 in temp:
					site_1,site_2,site_3,site_4,site_5,metal_site  = 0,0,0,0,0,0
					for atom in mol_1.GetAtoms():
						if atom.GetIdx()  == 5 and metal_site == 0:
							atom.SetAtomicNum(15)
							center_temp = atom.GetIdx()
							metal_site = 1
						if k!= 0:
							if atom.GetIdx()  == 1 and site_1 == 0:
								atom.SetAtomicNum(neighbours[0].GetAtomicNum())
								site_1 = 1
							elif atom.GetIdx()  == 2 and site_2 == 0:
								atom.SetAtomicNum(neighbours[j[0]].GetAtomicNum())
								site_2 = 1
							elif atom.GetIdx()  == 3 and site_3 == 0:
								atom.SetAtomicNum(neighbours[j[1]].GetAtomicNum())
								site_3 = 1
							elif atom.GetIdx()  == 4 and site_4 == 0:
								atom.SetAtomicNum(neighbours[j[2]].GetAtomicNum())
								site_4 = 1
							elif atom.GetIdx()  == 0 and site_5 == 0:
								atom.SetAtomicNum(neighbours[k].GetAtomicNum())
								site_5 = 1
						elif k == 0:
							if atom.GetIdx()  == 1 and site_1 == 0:
								atom.SetAtomicNum(neighbours[4].GetAtomicNum())
								site_1 = 1
							elif atom.GetIdx()  == 2 and site_2 == 0:
								atom.SetAtomicNum(neighbours[j[0]].GetAtomicNum())
								site_2 = 1
							elif atom.GetIdx()  == 3 and site_3 == 0:
								atom.SetAtomicNum(neighbours[j[1]].GetAtomicNum())
								site_3 = 1
							elif atom.GetIdx()  == 4 and site_4 == 0:
								atom.SetAtomicNum(neighbours[j[2]].GetAtomicNum())
								site_4 = 1
							elif atom.GetIdx() == 0 and site_5 == 0:
								atom.SetAtomicNum(neighbours[0].GetAtomicNum())
								site_5 = 1
						print('after')
						print(atom.GetSymbol(),atom.GetIdx())

					#assigning and embedding onto the core
					molecule_new, coordMap, algMap = template_embed_optimize(molecule,mol_1,args,log)

					for atom in molecule_new.GetAtoms():
						if atom.GetIdx() == center_idx:
							atom.SetAtomicNum(53)

					for atom in mol_1.GetAtoms():
						if atom.GetIdx() == center_temp:
							atom.SetAtomicNum(53)

					#writing to mol_object file
					name_final = name_input + str(name_1)+ str(name_2)
					mol_objects.append(molecule_new)
					name_return.append(name_final)
					coord_Map.append(coordMap)
					alg_Map.append(algMap)


					mol_template.append(mol_1)

	return mol_objects, name_return, coord_Map, alg_Map, mol_template

# TEMPLATE EMBED OPTIMIZE
def template_embed_optimize(molecule_embed,mol_1,args,log):

	#assigning and embedding onto the core
	num_atom_match = molecule_embed.GetSubstructMatch(mol_1)
	print(len(num_atom_match))

	#add H's to molecule
	molecule_embed = Chem.AddHs(molecule_embed)

	#definition of coordmap, the coreconfID(the firstone =-1)
	coordMap = {}
	coreConfId=-1
	randomseed=-1
	force_constant=10000

	# Choosing the type of force field
	for atom in molecule_embed.GetAtoms():
		if atom.GetAtomicNum() > 36: # up to Kr for MMFF, if not, the code will use UFF
			args.ff = "UFF"

	# Force field parameters
	if args.ff == "MMFF":
		GetFF = lambda mol,confId=-1:Chem.MMFFGetMoleculeForceField(mol,Chem.MMFFGetMoleculeProperties(mol),confId=-1)
	elif args.ff == "UFF":
		GetFF = lambda mol,confId=-1:Chem.UFFGetMoleculeForceField(mol,confId=-1)
	else:
		log.write('   Force field {} not supported!'.format(args.ff))
		sys.exit()
	getForceField=GetFF

	# This part selects which atoms from molecule are the atoms of the core
	try:
		coreConf = mol_1.GetConformer(coreConfId)
	except: pass
	for k, idxI in enumerate(num_atom_match):
		core_mol_1 = coreConf.GetAtomPosition(k)
		coordMap[idxI] = core_mol_1

	# This is the original version, if it doesn't work without coordMap I'll come back to it late
	if len(num_atom_match) == 5:
		ci = Chem.EmbedMolecule(molecule_embed, coordMap=coordMap, randomSeed=randomseed)
	if len(num_atom_match) == 6:
		#ignoreSmoothingFailures=True
		ci = Chem.EmbedMolecule(molecule_embed, coordMap=coordMap, randomSeed=randomseed,ignoreSmoothingFailures=True)
	if ci < 0:
		log.write('Could not embed molecule.')

	#algin molecule to the core
	algMap = [(k, l) for l, k in enumerate(num_atom_match)]

	ff = getForceField(molecule_embed, confId=-1)
	for k, idxI in enumerate(num_atom_match):
		for l in range(k + 1, len(num_atom_match)):
			idxJ = num_atom_match[l]
			d = coordMap[idxI].Distance(coordMap[idxJ])
			ff.AddDistanceConstraint(idxI, idxJ, d, d, force_constant)
	ff.Initialize()
	#reassignned n from 4 to 10 for better embed and minimzation
	n = 10
	more = ff.Minimize()
	while more and n:
		more = ff.Minimize()
		n -= 1
	# rotate the embedded conformation onto the core_mol:
	rdMolAlign.AlignMol(molecule_embed, mol_1, atomMap=algMap,reflect=True,maxIters=100)

	return molecule_embed, coordMap, algMap

# FUCNTION WORKING WITH MOL OBJECT TO CREATE CONFORMERS
def conformer_generation(mol,name,start_time,args,log,dup_data,dup_data_idx,coord_Map=None,alg_Map=None,mol_template=None):
	valid_structure = filters(mol, args,log)
	if valid_structure:
		if args.verbose:
			log.write("\n   ----- {} -----".format(name))

		try:
			# the conformational search
			gen = summ_search(mol, name,args,log,dup_data,dup_data_idx,coord_Map,alg_Map,mol_template)
			if gen != -1:
				if args.nodihedrals:
					if args.ANI1ccx != False:
						mult_min(name+'_'+'rdkit', args, 'ani',log,dup_data,dup_data_idx)
					if args.xtb != False:
						mult_min(name+'_'+'rdkit', args, 'xtb',log,dup_data,dup_data_idx)
				else:
					if args.ANI1ccx != False:
						if gen != 0:
							mult_min(name+'_'+'rdkit'+'_'+'rotated', args, 'ani',log,dup_data,dup_data_idx)
						else:
							log.write('\nx   No rotable dihydrals found. Using the non-rotated SDF for ANI')
							mult_min(name+'_'+'rdkit', args, 'ani',log,dup_data,dup_data_idx)
					if args.xtb != False:
						if gen !=0:
							mult_min(name+'_'+'rdkit'+'_'+'rotated', args, 'xtb',log,dup_data,dup_data_idx)
						else:
							log.write('\nx   No rotable dihydrals found. Using the non-rotated SDF for xTB')
							mult_min(name+'_'+'rdkit', args, 'xtb',log,dup_data,dup_data_idx)
			else:
				pass
		except (KeyboardInterrupt, SystemExit):
			raise
	else:
		log.write("ERROR: The structure is not valid")

	# removing temporary files
	temp_files = ['gfn2.out', 'xTB_opt.traj', 'ANI1_opt.traj', 'wbo', 'xtbrestart']
	for file in temp_files:
		if os.path.exists(file):
			os.remove(file)

	if args.time:
		log.write("\n Execution time: %s seconds" % (round(time.time() - start_time,2)))
		dup_data.at[dup_data_idx, 'time (seconds)'] = round(time.time() - start_time,2)

# RULES TO GET EXPERIMENTAL CONFORMERS
def exp_rules_output(mol, args,log):
	passing = True
	ligand_links = []
	atom_indexes = []
	for atom in mol.GetAtoms():
		# Finds the Ir atom and gets the atom types and indexes of all its neighbours
		if atom.GetSymbol() in args.metal:
			atomic_number = possible_atoms.index(atom.GetSymbol())
			atom.SetAtomicNum(atomic_number)
	for atom in mol.GetAtoms():
		if atom.GetAtomicNum() == atomic_number:
			metal_idx = atom.GetIdx()
			for x in atom.GetNeighbors():
				ligand_links.append(x.GetSymbol())
				atom_indexes.append(x.GetIdx())
	# I need to get the only 3D conformer generated in that mol object for rdMolTransforms
	mol_conf = mol.GetConformer(0)
	# This part will identify the pairs of C and N atoms that are part of the same Ph_Py ligand.
	# The shape of the atom pairs is '[[C1_ATOM_NUMBER, N1_ATOM_NUMBER],[C2, N2],...]'.
	# This information is required for the subsequent filtering process based on angles
	if len(atom_indexes) == args.complex_coord:
		ligand_atoms = []

		for i,_ in enumerate(atom_indexes):
			# This is a filter that excludes molecules that fell apart during DFT geometry
			# optimization (i.e. a N atom from one of the ligands separated from Ir). The
			# max distance allowed can be tuned in length_filter
			bond_length = rdMolTransforms.GetBondLength(mol_conf,metal_idx,atom_indexes[i])
			if ligand_links[i] == 'P':
				length_filter = 2.60
			else:
				length_filter = 2.25
			if bond_length > length_filter:
				passing = False
				break
			for j,_ in enumerate(atom_indexes):
				# Avoid combinations of the same atom with itself
				if atom_indexes[i] != atom_indexes[j]:
					# We know that the ligands never have 2 carbon atoms bonding the Ir atom. We
					# only use atom_indexes[i] for C atoms, and atom_indexes[j] for the potential
					# N atoms that are part of the same Ph_Py ligand
					if ligand_links[i] == 'C':
						# This part detects the Ir-C bond and breaks it, breaking the Ph_Py ring
						bond = mol.GetBondBetweenAtoms(atom_indexes[i], metal_idx)
						new_mol = Chem.FragmentOnBonds(mol, [bond.GetIdx()],addDummies=True, dummyLabels=[(atom_indexes[i], metal_idx)])
						if new_mol.GetAtomWithIdx(atom_indexes[i]).IsInRingSize(5) == True:
							five_mem = True
						else:
							five_mem = False
						# Now, identify whether or not the initial 5-membered ring formed between
						# [-Ir-C-C-C-N-] is broken when we break the Ir-C bond. This works
						# because Ph_Py units bind Ir in the same way always, through 1 C and 1 N
						# that are in the same position, forming a 5-membered ring.
						# If this ring is broken, atom_indexes[j] will not be part of a
						# 5-membered ring (atom.IsInRingSize(5) == False) which means that
						# this atom was initially inside the same ligand as the
						# parent C of atom_indexes[i])
						if five_mem == False:
							if new_mol.GetAtomWithIdx(atom_indexes[j]).IsInRingSize(5) == False:
								bond_2 = mol.GetBondBetweenAtoms(atom_indexes[j], metal_idx)
								new_mol_2 = Chem.FragmentOnBonds(mol, [bond_2.GetIdx()],addDummies=True, dummyLabels=[(atom_indexes[j], metal_idx)])
								#doing backwards as well eg. Ir N bond
								if new_mol_2.GetAtomWithIdx(atom_indexes[i]).IsInRingSize(5) == False:
									ligand_atoms.append([atom_indexes[i],atom_indexes[j]])
									break
						else:
							if new_mol.GetAtomWithIdx(atom_indexes[j]).IsInRingSize(5) == False:
								ligand_atoms.append([atom_indexes[i],atom_indexes[j]])
								break
		if passing == True:
			# This stop variable and the breaks inside the inner loops will make that if there
			# is one angle that does not meet the criteria for valid conformers, the outter (i)
			# and inner (j) loops will stop simultaneously (saves time since the molecule is
			# already an invalid geometry, it does not make sense to keep iterating)
			stop = False
			# For complexes with 3 Ph_Py ligands:
			if len(ligand_atoms) == 3:
				for i,_ in enumerate(ligand_atoms):
					if stop != True:
						for j, lig_atmo_j in enumerate(ligand_atoms):
							# the i<=j part avoids repeating atoms, the i != j part avoid angles
							# containing the same number twice (i.e. 4-16-4, this angle will fail)
							if i <= j and i != j:
								# Calculate the angle between 2 N atoms from different Ph_Py ligands.
								# When there are 3 Ph_Py ligands, no 2 N atoms must be in 180 degrees
								angle = rdMolTransforms.GetAngleDeg(mol_conf,ligand_atoms[i][1],metal_idx,ligand_atoms[j][1])
								if (180 - args.angle_off) <= angle <= (180 + args.angle_off):
									passing = False
									break
			# For complexes with 2 Ph_Py ligands + 1 ligand that is not Ph_Py
			if len(ligand_atoms) == 2:
				# Since there are only 2 N atoms, we do not need to include a nested loop
					angle = rdMolTransforms.GetAngleDeg(mol_conf,ligand_atoms[0][1],metal_idx,ligand_atoms[1][1])
					# Calculate the angle between 2 N atoms from different Ph_Py ligands.
					# When there are 2 Ph_Py ligands, the 2 N atoms from the 2 Ph_Py ligands
					# must be in 180 degrees
					if (180 - args.angle_off) <= angle <= (180 + args.angle_off):
						pass
					else:
						passing = False
	# This is a second filter that excludes molecules that fell apart during DFT geometry
	# optimization (i.e. a N atom from one of the ligands separated from Ir). In this case,
	# it filters off molecules that the SDF only detects 5 Ir neighbours
	else:
		passing = False
	return passing

# FILTER TO BE APPLIED FOR SMILES
def filters(mol,args,log):
	valid_structure = True
	# Second filter: molecular weight
	if Descriptors.MolWt(mol) < args.max_MolWt:
		# Third filter: this filters salts off (2 separated components)
		#if len(Chem.MolToSmiles(mol).split('.')) == 1:
		for atom in mol.GetAtoms():
			#Fourth filter: atoms outside the scope chosen in 'possible_atoms'
			if atom.GetSymbol() not in possible_atoms:
				valid_structure = False
				if args.verbose:
					log.write(" Exiting as atom isn't in atoms in the periodic table")
	else:
		valid_structure = False
		if args.verbose:
			log.write(" Exiting as total molar mass > {0}".format(args.max_MolWt))
	return valid_structure

# PARSES THE ENERGIES FROM SDF FILES
def read_energies(file,log): # parses the energies from sdf files - then used to filter conformers
	energies = []
	f = open(file,"r")
	readlines = f.readlines()
	for i,_ in enumerate(readlines):
		if readlines[i].find('>  <Energy>') > -1:
			energies.append(float(readlines[i+1].split()[0]))
	f.close()
	return energies

def header_com(name,lot,bs,bs_gcp, args, log, input_sp, input, genecp):
	#chk option
	if args.chk:
		if args.single_point:
			if genecp != 'None':
				header = [
					'%chk={}.chk'.format(name),
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ genecp + ' '+ input_sp ]
			else:
				header = [
					'%chk={}.chk'.format(name),
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ bs + ' '+ input_sp ]
		else:
			if genecp != 'None':
				header = [
						'%chk={}.chk'.format(name),
						'%mem={}'.format(args.mem),
						'%nprocshared={}'.format(args.nprocs),
						'# {0}'.format(lot)+ '/'+ genecp + ' '+ input ]
			else:
				header = [
						'%chk={}.chk'.format(name),
						'%mem={}'.format(args.mem),
						'%nprocshared={}'.format(args.nprocs),
						'# {0}'.format(lot)+ '/'+ bs + ' '+ input ]
	else:
		if args.single_point:
			if genecp != 'None':
				header = [
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ genecp + ' '+ input_sp ]
			else:
				header = [
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ bs + ' '+ input_sp ]

		else:
			if genecp != 'None':
				header = [
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ genecp + ' '+ input ]
			else:
				header = [
					'%mem={}'.format(args.mem),
					'%nprocshared={}'.format(args.nprocs),
					'# {0}'.format(lot)+ '/'+ bs + ' '+ input ]
	return header

def convert_sdf_to_com(path_for_file,file,com,com_low,energies,header,args):

	if args.lowest_only:
		subprocess.run(
			  ['obabel', '-isdf', path_for_file+file, '-ocom', '-O'+com_low,'-l' , '1', '-xk', '\n'.join(header)]) #takes the lowest conformer which is the first in the file
	elif args.lowest_n:
		no_to_write = 0
		if len(energies) != 1:
			for i,_ in enumerate(energies):
				energy_diff = energies[i] - energies[0]
				if energy_diff < args.energy_threshold_for_gaussian: # thershold is in kcal/mol and energies are in kcal/mol as well
					no_to_write +=1
			subprocess.run(
				 ['obabel', '-isdf', path_for_file+file, '-f', '1', '-l' , str(no_to_write), '-osdf', '-Otemp.sdf'])
			subprocess.run(
				  ['obabel', '-isdf', 'temp.sdf', '-ocom', '-O'+com,'-m', '-xk', '\n'.join(header)])
		else:
			subprocess.run(
				  ['obabel', '-isdf', path_for_file+file, '-ocom', '-O'+com,'-m', '-xk', '\n'.join(header)])
	else:
		subprocess.run(
			  ['obabel', '-isdf', path_for_file+file, '-ocom', '-O'+com,'-m', '-xk', '\n'.join(header)])

def input_line(args):
	#definition of input lines
	if args.frequencies:
		if args.dispersion_correction:
			if args.solvent_model == 'gas_phase':
				input = 'opt=(maxcycles={0}) freq=noraman empiricaldispersion={1}'.format(args.max_cycle_opt,args.empirical_dispersion)
				input_sp = 'nmr=giao empiricaldispersion={0}'.format(args.empirical_dispersion)  #input for single point nmr
			else :
				input = 'opt=(maxcycles={0}) freq=noraman scrf=({1},solvent={2}) empiricaldispersion={3}'.format(args.max_cycle_opt, args.solvent_model, args.solvent_name,args.empirical_dispersion ) #add solvent if needed
				input_sp = 'scrf=({0},solvent={1}) nmr=giao empiricaldispersion={2}'.format(args.solvent_model, args.solvent_name, args.empirical_dispersion)  ##add solvent if needed
		else:
			if args.solvent_model == 'gas_phase':
				input = 'opt=(maxcycles={0}) freq=noraman'.format(args.max_cycle_opt)
				input_sp = 'nmr=giao ' #input for single point nmr
			else :
				input = 'opt=(maxcycles={0}) freq=noraman scrf=({1},solvent={2})'.format(args.max_cycle_opt,args.solvent_model, args.solvent_name) #add solvent if needed
				input_sp = 'scrf=({0},solvent={1}) nmr=giao'.format(args.solvent_model, args.solvent_name)  ##add solvent if needed
	else:
		if args.dispersion_correction:
			if args.solvent_model == 'gas_phase':
				input = 'opt=(maxcycles={0}) empiricaldispersion={1}'.format(args.max_cycle_opt,args.empirical_dispersion)
				input_sp = 'nmr=giao empiricaldispersion={0}'.format(args.empirical_dispersion)  #input for single point nmr
			else :
				input = 'opt=(maxcycles={0}) scrf=({1},solvent={2}) empiricaldispersion={3}'.format(args.max_cycle_opt,args.solvent_model, args.solvent_name,args.empirical_dispersion ) #add solvent if needed
				input_sp = 'scrf=({0},solvent={1}) nmr=giao empiricaldispersion={2}'.format(args.solvent_model, args.solvent_name, args.empirical_dispersion)  ##add solvent if needed
		else:
			if args.solvent_model == 'gas_phase':
				input = 'opt=(maxcycles={0})'.format(args.max_cycle_opt)
				input_sp = 'nmr=giao ' #input for single point nmr
			else :
				input = 'opt=(maxcycles={0}) scrf=({1},solvent={2})'.format(args.max_cycle_opt,args.solvent_model, args.solvent_name) #add solvent if needed
				input_sp = 'scrf=({0},solvent={1}) nmr=giao'.format(args.solvent_model, args.solvent_name)  ##add solvent if needed
	return input, input_sp

# MAIN FUNCTION TO CREATE GAUSSIAN JOBS
def write_gaussian_input_file(file, name,lot, bs, bs_gcp, energies, args,log,charge_data):

	#find location of molecule and respective scharges
	name_list = name.split('_')
	if 'xtb' or 'ani' in name_list:
		name_molecule = name[:-4]
	if 'rdkit' in name_list:
		name_molecule = name[:-6]
	if 'rotated' in name_list:
		name_molecule = name[:-14]

	for i in range(len(charge_data)):
		if charge_data.loc[i,'Molecule'] == name_molecule:
			charge_com = charge_data.loc[i,'Overall charge']

	input, input_sp = input_line(args)

	#defining genecp
	genecp = 'None'

	try:
		#reading the sdf to check for I atom_symbol
		suppl = Chem.SDMolSupplier(file)
		for atom in suppl[0].GetAtoms():
			if atom.GetSymbol() in args.genecp_atoms:
				genecp = 'genecp'
				break
			elif atom.GetSymbol() in args.gen_atoms:
				genecp = 'gen'
				break
	except:
		read_lines = open(file,"r").readlines()
		for line,_ in enumerate(read_lines):
			for atom in args.genecp_atoms:
				if read_lines[line].find(atom)>-1:
					genecp = 'genecp'
					break
			for atom in args.gen_atoms:
				if read_lines[line].find(atom)>-1:
					genecp = 'gen'
					break

	if args.single_point:
		#pathto change to
		path_write_gjf_files = 'generated_sp_files/' + str(lot) + '-' + str(bs)
		#log.write(path_write_gjf_files)
		os.chdir(path_write_gjf_files)
	else:
		#path to change to
		path_write_gjf_files = 'generated_gaussian_files/' + str(lot) + '-' + str(bs)
		os.chdir(path_write_gjf_files)

	path_for_file = '../../'

	com = '{0}_.com'.format(name)
	com_low = '{0}_low.com'.format(name)

	header = header_com(name,lot, bs, bs_gcp,args,log,input_sp, input, genecp)

	convert_sdf_to_com(path_for_file,file,com,com_low,energies,header,args)

	com_files = glob.glob('{0}_*.com'.format(name))

	for file in com_files:
		if genecp =='genecp' or genecp == 'gen':
			ecp_list,ecp_genecp_atoms,ecp_gen_atoms = [],False,False
			read_lines = open(file,"r").readlines()

			#chaanging the name of the files to the way they are in xTB Sdfs
			#getting the title line
			for i in range(0,len(read_lines)):
				if len(read_lines[i].strip()) == 0:
					title_line = read_lines[i+1]
					title_line = title_line.lstrip()
					rename_file_name = title_line.replace(" ", "_")
					break

			rename_file_name = rename_file_name.strip()+'.com'

			#change charge and multiplicity for Octahydrasl
			if args.metal_complex:
				for i in range(0,len(read_lines)):
					if len(read_lines[i].strip()) == 0:
						read_lines[i+3] = str(charge_com)+' '+ str(args.complex_spin)+'\n'
						break
				out = open(file, 'w')
				out.writelines(read_lines)
				out.close()
				read_lines = open(file,"r").readlines()

			fileout = open(file, "a")
			# Detect if there are I atoms to use genecp or not (to use gen)
			for i in range(4,len(read_lines)):
				if read_lines[i].split(' ')[0] not in ecp_list and read_lines[i].split(' ')[0] in possible_atoms:
					ecp_list.append(read_lines[i].split(' ')[0])
				if read_lines[i].split(' ')[0] in args.genecp_atoms:
				   ecp_genecp_atoms = True
				if read_lines[i].split(' ')[0] in args.gen_atoms:
				   ecp_gen_atoms = True

			#error if both genecp and gen are
			if ecp_genecp_atoms and ecp_gen_atoms:
				sys.exit("ERROR: Can't use Gen and GenECP at the same time")

			for i in range(len(ecp_list)):
				if ecp_list[i] not in (args.genecp_atoms or args.gen_atoms):
					fileout.write(ecp_list[i]+' ')
			fileout.write('0\n')
			fileout.write(bs+'\n')
			fileout.write('****\n')
			if ecp_genecp_atoms == False and ecp_gen_atoms == False :
				fileout.write('\n')
			else:
				if len(bs_gcp.split('.')) > 1:
					if bs_gcp.split('.')[1] == 'txt' or bs_gcp.split('.')[1] == 'yaml':
						os.chdir(path_for_file)
						read_lines = open(bs_gcp,"r").readlines()
						os.chdir(path_write_gjf_files)
						#chaanging the name of the files to the way they are in xTB Sdfs
						#getting the title line
						for line in read_lines:
							fileout.write(line)
						fileout.write('\n\n')
				else:
					for i in range(len(ecp_list)):
						if ecp_list[i] in args.genecp_atoms :
							fileout.write(ecp_list[i]+' ')
						elif ecp_list[i] in args.gen_atoms :
							fileout.write(ecp_list[i]+' ')
					fileout.write('0\n')
					fileout.write(bs_gcp+'\n')
					fileout.write('****\n\n')
					if ecp_genecp_atoms:
						for i in range(len(ecp_list)):
							if ecp_list[i] in args.genecp_atoms:
								fileout.write(ecp_list[i]+' ')
						fileout.write('0\n')
						fileout.write(bs_gcp+'\n\n')
			fileout.close()

		else:
			read_lines = open(file,"r").readlines()

			#changing the name of the files to the way they are in xTB Sdfs
			#getting the title line
			for i in range(0,len(read_lines)):
				if len(read_lines[i].strip()) == 0:
					title_line = read_lines[i+1]
					title_line = title_line.lstrip()
					rename_file_name = title_line.replace(" ", "_")
					break

			rename_file_name = rename_file_name.strip()+'.com'

			#change charge and multiplicity for Octahydrasl
			if args.metal_complex:
				for i,_ in enumerate(read_lines):
					if len(read_lines[i].strip()) == 0:
						read_lines[i+3] = str(charge_com)+' '+ str(args.complex_spin)+'\n'
						break
				out = open(file, 'w')
				out.writelines(read_lines)
				out.close()

		#change file by moving to new file
		os.rename(file,rename_file_name)

		#submitting the gaussian file on summit
		if args.qsub:
			os.system(args.submission_command + rename_file_name)

	os.chdir(path_for_file)

# CHECKS THE FOLDER OF FINAL LOG FILES
def check_for_final_folder(w_dir,log):
	dir_found = False
	while dir_found == False:
		temp_dir = w_dir+'New_Gaussian_Input_Files/'
		if os.path.isdir(temp_dir):
			w_dir = temp_dir
		else:
			dir_found =True
	return w_dir

def moving_log_files(source, destination, file):
	try:
		os.makedirs(destination)
		shutil.move(source, destination)
	except OSError:
		if  os.path.isdir(destination) and not os.path.exists(destination+file):
			shutil.move(source, destination)
		else:
			raise

def moving_sdf_files(destination,src,file):
	try:
		os.makedirs(destination)
		shutil.move(os.path.join(src, file), os.path.join(destination, file))
	except OSError:
		if  os.path.isdir(destination):
			shutil.move(os.path.join(src, file), os.path.join(destination, file))
		else:
			raise

# DEFINTION OF OUTPUT ANALYSER and NMR FILES CREATOR
def output_analyzer(log_files, w_dir, lot, bs,bs_gcp, args, w_dir_fin,log):

	input, input_sp = input_line(args)

	for file in log_files:
		print(file)

		#made it global for all functions
		rms = 10000
		#defined the variable stop_rms, standor
		stop_rms = 0
		standor = 0
		NATOMS = 0

		outfile = open(file,"r")
		outlines = outfile.readlines()
		ATOMTYPES, CARTESIANS = [],[]
		FREQS, REDMASS, FORCECONST, NORMALMODE = [],[],[],[]
		IM_FREQS = 0
		freqs_so_far = 0
		TERMINATION = "unfinished"
		ERRORTYPE = 'unknown'
		stop_name,stop_term=0,0

		# only for name an and charge
		for i in range(0,len(outlines)):
			if stop_name == 2:
				break
			# Get the name of the compound (specified in the title)
			if outlines[i].find('Symbolic Z-matrix:') > -1:
				name = outlines[i-2]
				print(name)
				stop_name=stop_name+1
			# Determine charge and multiplicity
			if outlines[i].find("Charge = ") > -1:
				CHARGE = int(outlines[i].split()[2])
				MULT = int(outlines[i].split()[5].rstrip("\n"))
				stop_name=stop_name+1
				print(CHARGE,MULT)

		#Change to reverse for termination
		for i in reversed(range(0,len(outlines))):
			if stop_term == 1:
				break
			# Determine the kind of job termination
			if outlines[i].find("Normal termination") > -1:
				TERMINATION = "normal"
				stop_term=stop_term+1
			elif outlines[i].find("Error termination") > -1:
				TERMINATION = "error"
				if outlines[i-1].find("Atomic number out of range") > -1:
					ERRORTYPE = "atomicbasiserror"
				if outlines[i-3].find("SCF Error SCF Error SCF Error SCF Error SCF Error SCF Error SCF Error SCF Error") > -1:
					ERRORTYPE = "SCFerror"
				stop_term=stop_term+1
		#log.write(TERMINATION)

		###reverse
		stop_get_details_stand_or = 0
		stop_get_details_dis_rot = 0
		stop_get_details_freq = 0
		for i in reversed(range(0,len(outlines))):
			if TERMINATION == "normal":
				if stop_get_details_stand_or == 1 and stop_get_details_dis_rot == 1 and stop_get_details_freq == 1:
					break
				# Sets where the final coordinates are inside the file
				###if outlines[i].find("Input orientation") > -1: standor = i
				if stop_get_details_dis_rot !=1 and (outlines[i].find("Distance matrix") > -1 or outlines[i].find("Rotational constants") >-1) :
					if outlines[i-1].find("-------") > -1:
						disrotor = i
						stop_get_details_dis_rot += 1
				if outlines[i].find("Standard orientation") > -1 and stop_get_details_stand_or !=1 :
					standor = i
					NATOMS = disrotor-i-6
					#log.write(NATOMS)
					stop_get_details_stand_or += 1
				# Get the frequencies and identifies negative frequencies
				if outlines[i].find(" Frequencies -- ") > -1 and stop_get_details_freq != 1:
					nfreqs = len(outlines[i].split())
					for j in range(2, nfreqs):
						FREQS.append(float(outlines[i].split()[j]))
						NORMALMODE.append([])
						if float(outlines[i].split()[j]) < 0.0:
							IM_FREQS += 1
					for j in range(3, nfreqs+1):
						REDMASS.append(float(outlines[i+1].split()[j]))
					for j in range(3, nfreqs+1):
						FORCECONST.append(float(outlines[i+2].split()[j]))
					for j in range(0,NATOMS):
						for k in range(0, nfreqs-2):
							NORMALMODE[(freqs_so_far + k)].append([float(outlines[i+5+j].split()[3*k+2]), float(outlines[i+5+j].split()[3*k+3]), float(outlines[i+5+j].split()[3*k+4])])
					freqs_so_far = freqs_so_far + nfreqs - 2
					stop_get_details_freq += 1
			if TERMINATION != "normal":
				if outlines[i].find('Cartesian Forces:  Max') > -1:
					if float(outlines[i].split()[5]) < rms:
						rms = float(outlines[i].split()[5])
						stop_rms = i

		if TERMINATION == "normal":
			# Get the coordinates for jobs that finished well with and without imag. freqs
			try:
				standor
			except NameError:
				pass
			else:
				for i in range(standor+5,standor+5+NATOMS):
					massno = int(outlines[i].split()[1])
					if massno < len(possible_atoms):
						atom_symbol = possible_atoms[massno]
					else:
						atom_symbol = "XX"
					ATOMTYPES.append(atom_symbol)
					CARTESIANS.append([float(outlines[i].split()[3]), float(outlines[i].split()[4]), float(outlines[i].split()[5])])


		if TERMINATION != "normal":
			# Get he coordinates for jobs that did not finished or finished with an error
			if stop_rms == 0:
				last_line = len(outlines)
				log.write('lastline')
			else:
				last_line = stop_rms
				log.write('stoprms')
			stop_get_details_stand_or = 0
			stop_get_details_dis_rot = 0
			for i in reversed(range(0,last_line)):
				if stop_get_details_stand_or == 1 and stop_get_details_dis_rot == 1 and stop_get_details_freq == 1:
					break
				# Sets where the final coordinates are inside the file
				if outlines[i].find("Standard orientation") > -1 and stop_get_details_stand_or != 1:
					standor = i
					NATOMS = disrotor-i-6
					stop_get_details_stand_or += 1
				if stop_get_details_stand_or != 1 and (outlines[i].find("Distance matrix") > -1 or outlines[i].find("Rotational constants") >-1):
					if outlines[i-1].find("-------") > -1:
						#log.write(i)
						disrotor = i
						stop_get_details_dis_rot += 1
			###no change after this
			for i in range (standor+5,standor+5+NATOMS):
				massno = int(outlines[i].split()[1])
				if massno < len(possible_atoms):
					atom_symbol = possible_atoms[massno]
				else:
					atom_symbol = "XX"
				ATOMTYPES.append(atom_symbol)
				CARTESIANS.append([float(outlines[i].split()[3]), float(outlines[i].split()[4]), float(outlines[i].split()[5])])

		# This part fixes jobs with imaginary freqs
		if IM_FREQS > 0:
			# Multiplies the imaginary normal mode vector by this amount (from -1 to 1).
			amplitude = 0.2 # default in pyQRC
			shift = []

			# Save the original Cartesian coordinates before they are altered
			orig_carts = []
			for atom in range(0,NATOMS):
				orig_carts.append([CARTESIANS[atom][0], CARTESIANS[atom][1], CARTESIANS[atom][2]])

			# could get rid of atomic units here, if zpe_rat definition is changed
			for mode,_ in enumerate(FREQS):
				# Either moves along any and all imaginary freqs, or a specific mode requested by the user
				if FREQS[mode] < 0.0:
					shift.append(amplitude)
				else:
					shift.append(0.0)

			# The starting geometry is displaced along the each normal mode according to the random shift
				for atom in range(0,NATOMS):
					for coord in range(0,3):
						CARTESIANS[atom][coord] = CARTESIANS[atom][coord] + NORMALMODE[mode][atom][coord] * shift[mode]
		outfile.close()

		# This part places the calculations in different folders depending on the type of
		# termination and number of imag. freqs
		source = w_dir+file

		if IM_FREQS == 0 and TERMINATION == "normal":
			destination = w_dir_fin
			moving_log_files(source,destination, file)

		if IM_FREQS > 0:
			destination = w_dir+'imaginary_frequencies/'
			moving_log_files(source,destination, file)

		if IM_FREQS == 0 and TERMINATION == "error":
			if stop_rms == 0 and ERRORTYPE == "atomicbasiserror":
				destination = w_dir+'failed_error/atomic_basis_error'
			elif stop_rms == 0 and ERRORTYPE == "SCFerror":
				destination = w_dir+'failed_error/SCF_error'
			else:
				destination = w_dir+'failed_error/unknown_error'
			moving_log_files(source,destination, file)

		if IM_FREQS == 0 and TERMINATION == "unfinished":
			destination = w_dir+'failed_unfinished/'
			moving_log_files(source,destination, file)

		if IM_FREQS > 0 or TERMINATION != "normal" and not os.path.exists(w_dir+'failed_error/atomic_basis_error/'+file):

			# creating new folder with new input gaussian files
			new_gaussian_input_files = w_dir+'new_gaussian_input_files'

			try:
				os.makedirs(new_gaussian_input_files)
			except OSError:
				if  os.path.isdir(new_gaussian_input_files):
					os.chdir(new_gaussian_input_files)
				else:
					raise

			os.chdir(new_gaussian_input_files)

			log.write('-> Creating new gaussian input files for {0}/{1} file {2}'.format(lot,bs,name))

			# Options for genecp
			ecp_list,ecp_genecp_atoms,ecp_gen_atoms,genecp = [],False,False,None

			for i in range(len(ATOMTYPES)):
				if ATOMTYPES[i] not in ecp_list and ATOMTYPES[i] in possible_atoms:
					ecp_list.append(ATOMTYPES[i])
				if ATOMTYPES[i] in args.genecp_atoms:
				   ecp_genecp_atoms = True
				if ATOMTYPES[i] in args.gen_atoms:
				   ecp_gen_atoms = True
			if ecp_gen_atoms == True:
				genecp = 'gen'
			if ecp_genecp_atoms == True:
				genecp = 'genecp'

			#error if both genecp and gen are
			if ecp_genecp_atoms and ecp_gen_atoms:
				sys.exit("ERROR: Can't use Gen and GenECP at the same time")

			if ERRORTYPE == 'SCFerror':
				if genecp == 'genecp' or  genecp == 'gen':
					if args.single_point:
						keywords_opt = lot +'/'+ genecp+' '+ input_sp + 'SCF=QC'
					else:
						keywords_opt = lot +'/'+ genecp+' '+ input + 'SCF=QC'
				else:
					if args.single_point:
						keywords_opt = lot +'/'+ bs+' '+ input_sp + 'SCF=QC'
					else:
						keywords_opt = lot +'/'+ bs+' '+ input + 'SCF=QC'
			else:
				if genecp == 'genecp' or  genecp == 'gen':
					if args.single_point:
						keywords_opt = lot +'/'+ genecp+' '+ input_sp
					else:
						keywords_opt = lot +'/'+ genecp+' '+ input
				else:
					if args.single_point:
						keywords_opt = lot +'/'+ bs +' '+ input_sp
					else:
						keywords_opt = lot +'/'+ bs +' '+ input
			fileout = open(file.split(".")[0]+'.com', "w")
			fileout.write("%mem="+str(args.mem)+"\n")
			fileout.write("%nprocshared="+str(args.nprocs)+"\n")
			fileout.write("# "+keywords_opt+"\n")
			fileout.write("\n")
			fileout.write(name+"\n")
			fileout.write(str(CHARGE)+' '+str(MULT)+'\n')
			for atom in range(0,NATOMS):
				fileout.write('{0:>2} {1:12.8f} {2:12.8f} {3:12.8f}'.format(ATOMTYPES[atom], CARTESIANS[atom][0],  CARTESIANS[atom][1],  CARTESIANS[atom][2]))
				fileout.write("\n")
			fileout.write("\n")
			if genecp == 'genecp' or  genecp == 'gen':
				for i in range(len(ecp_list)):
					if ecp_list[i] not in (args.genecp_atoms or args.gen_atoms):
						fileout.write(ecp_list[i]+' ')
				fileout.write('0\n')
				fileout.write(bs+'\n')
				fileout.write('****\n')
				if ecp_genecp_atoms == False and ecp_gen_atoms == False :
					fileout.write('\n')
				else:
					if len(bs_gcp.split('.')) > 1:
						if bs_gcp.split('.')[1] == 'txt' or bs_gcp.split('.')[1] == 'yaml':
							os.chdir(path_for_file)
							read_lines = open(bs_gcp,"r").readlines()
							os.chdir(path_write_gjf_files)
							#chaanging the name of the files to the way they are in xTB Sdfs
							#getting the title line
							for line in read_lines:
								fileout.write(line)
							fileout.write('\n\n')
					else:
						for i in range(len(ecp_list)):
							if ecp_list[i] in args.genecp_atoms :
								fileout.write(ecp_list[i]+' ')
							elif ecp_list[i] in args.gen_atoms :
								fileout.write(ecp_list[i]+' ')
						fileout.write('0\n')
						fileout.write(bs_gcp+'\n')
						fileout.write('****\n\n')
						if ecp_genecp_atoms:
							for i in range(len(ecp_list)):
								if ecp_list[i] in args.genecp_atoms:
									fileout.write(ecp_list[i]+' ')
						fileout.write('0\n')
						fileout.write(bs_gcp+'\n\n')
				fileout.close()
			else:
				fileout.close()

		#changing directory back to where all files are from new files created.
		os.chdir(w_dir)

		#adding in the NMR componenet only to the finished files after reading from normally finished log files
		if args.sp and TERMINATION == "normal":

			# creating new folder with new input gaussian files
			single_point_input_files = w_dir+'/single_point_input_files'

			try:
				os.makedirs(single_point_input_files)
			except OSError:
				if  os.path.isdir(single_point_input_files):
					os.chdir(single_point_input_files)
				else:
					raise

			os.chdir(single_point_input_files)
			log.write('Creating new single point files files for {0}/{1} file {2}'.format(lot,bs,name))

			# Options for genecp
			ecp_list,ecp_genecp_atoms, ecp_gen_atoms,genecp = [],False,False,None

			for i,_ in enumerate(ATOMTYPES):
				if ATOMTYPES[i] not in ecp_list and ATOMTYPES[i] in possible_atoms:
					ecp_list.append(ATOMTYPES[i])
				if ATOMTYPES[i] in args.genecp_atoms:
				   ecp_genecp_atoms = True
				if ATOMTYPES[i] in args.gen_atoms:
				   ecp_gen_atoms = True
			if ecp_gen_atoms == True:
				genecp = 'gen'
			if ecp_genecp_atoms == True:
				genecp = 'genecp'

			keywords_opt =  args.input_for_sp

			fileout = open(file.split(".")[0]+'.com', "w")
			fileout.write("%mem="+str(args.mem)+"\n")
			fileout.write("%nprocshared="+str(args.nprocs)+"\n")
			fileout.write("# "+keywords_opt+"\n")
			fileout.write("\n")
			fileout.write(name+"\n")
			fileout.write(str(CHARGE)+' '+str(MULT)+'\n')
			for atom in range(0,NATOMS):
				fileout.write('{0:>2} {1:12.8f} {2:12.8f} {3:12.8f}'.format(ATOMTYPES[atom], CARTESIANS[atom][0],  CARTESIANS[atom][1],  CARTESIANS[atom][2]))
				fileout.write("\n")
			fileout.write("\n")
			if genecp =='genecp' or genecp =='gen':
				for i,_ in enumerate(ecp_list):
					if ecp_list[i] not in (args.genecp_atoms or args.gen_atoms):
						fileout.write(ecp_list[i]+' ')
				fileout.write('0\n')
				fileout.write(bs+'\n')
				fileout.write('****\n')
				if ecp_genecp_atoms == False and ecp_gen_atoms == False :
					fileout.write('\n')
				else:
					if len(bs_gcp.split('.')) > 1:
						if bs_gcp.split('.')[1] == 'txt' or bs_gcp.split('.')[1] == 'yaml':
							os.chdir(path_for_file)
							read_lines = open(bs_gcp,"r").readlines()
							os.chdir(path_write_gjf_files)
							#chaanging the name of the files to the way they are in xTB Sdfs
							#getting the title line
							for line in read_lines:
								fileout.write(line)
							fileout.write('\n\n')
					else:
						for i in range(len(ecp_list)):
							if ecp_list[i] in args.genecp_atoms :
								fileout.write(ecp_list[i]+' ')
							elif ecp_list[i] in args.gen_atoms :
								fileout.write(ecp_list[i]+' ')
						fileout.write('0\n')
						fileout.write(bs_gcp+'\n')
						fileout.write('****\n\n')
						if ecp_genecp_atoms:
							for i in range(len(ecp_list)):
								if ecp_list[i] in args.genecp_atoms:
									fileout.write(ecp_list[i]+' ')
						fileout.write('0\n')
						fileout.write(bs_gcp+'\n\n')
				fileout.close()
			else:
				fileout.write("\n")

		#changing directory back to where all files are from new files created.
		os.chdir(w_dir)

# CALCULATION OF BOLTZMANN FACTORS
def boltz_calculation(val,i,log):
	#need to have good vibes
	cmd = 'python' +  ' -m' + ' goodvibes' + ' --csv' + ' --boltz ' +'--output ' + str(i) + ' ' + val
	os.system(cmd)

# CHECKING FOR DUPLICATES
def dup_calculation(val,w_dir, agrs,log):
	#need to have good vibes
	cmd = 'python' +  ' -m' + ' goodvibes' + ' --dup ' + ' ' + val + '>' + ' ' + 'duplicate_files_checked.txt'
	os.system(cmd)

	#reading the txt files to get the DUPLICATES
	dup_file_list = []
	dupfile = open('duplicate_files_checked.txt',"r")
	duplines = dupfile.readlines()

	for i,_ in enumerate(duplines):
		if duplines[i].find('duplicate') > -1:
			dup_file_list.append(duplines[i].split(' ')[1])

	#move the files to specific directory
	destination = w_dir+'Duplicates/'
	for source in dup_file_list:
		try:
			os.makedirs(destination)
			shutil.move(source, destination)
		except OSError:
			if  os.path.isdir(destination) and not os.path.exists(destination):
				shutil.move(source, destination)
			else:
				raise

# COMBINING FILES FOR DIFFERENT MOLECULES
def combine_files(csv_files, lot, bs, args,log):
	#final dataframe with only the boltzmann averaged values
	final_file_avg_thermo_data = pd.DataFrame(columns=columns)
	compare_G = pd.DataFrame(columns=['Structure_of_min_conf','min_qh-G(T)','boltz_avg_qh-G(T)'])

	files = []
	#combine all the csv_files

	for f in csv_files:

		log.write(f)

		df = pd.read_csv(f, skiprows = 16)
		# df['Structure']= df['Structure'].astype(str)
		df = df.rename(columns={"   Structure": "Structure"})

		#dropping the ************* line
		df = df.drop(df.index[0])
		df.iloc[-1] = np.nan

		for col in columns:
			if col == 'Structure':
				#identifyin the minmum energy if the conformers
				min_G = df['qh-G(T)'].min()
				#getting the name of the structure of the min G
				idx_name_of_min_conf = df['qh-G(T)'].idxmin() - 1
				name_of_min_conf = df.iloc[idx_name_of_min_conf]['Structure']

			elif col != 'Structure':
				boltz_avg = np.sum(df[col] * df['Boltz'])
				df.at[df.index[-1], col] = boltz_avg
				if col == 'qh-G(T)':
					compare_G = compare_G.append({'Structure_of_min_conf': name_of_min_conf,'min_qh-G(T)': min_G,'boltz_avg_qh-G(T)': boltz_avg}, ignore_index=True)

		final_file_avg_thermo_data = final_file_avg_thermo_data.append({'Structure':name_of_min_conf , 'E': df.iloc[-1]['E'] , 'ZPE': df.iloc[-1]['ZPE'], 'H':df.iloc[-1]['H'] , 'T.S':df.iloc[-1]['T.S'] , 'T.qh-S':df.iloc[-1]['T.qh-S'] , 'G(T)': df.iloc[-1]['G(T)'], 'qh-G(T)':df.iloc[-1]['qh-G(T)'] },ignore_index=True)

		files.append(df)

	final_file_all_data = pd.concat(files, axis=0, ignore_index=True)

	#combined_csv = pd.concat([pd.read_csv(f, skiprows = 14, skipfooter = 1) for f in csv_files ])
	#change directory to write all files in one place
	destination = args.path+'All csv files/'+ str(lot)+ '-'+ str(bs)
	try:
		os.makedirs(destination)
	except OSError:
		if  os.path.isdir(destination):
			pass
		else:
			raise
	os.chdir(destination)

	#export to csv
	final_file_all_data.to_csv( str(lot) + '-' + str(bs) + '_all_molecules_all data.csv', index=False, encoding='utf-8-sig')
	final_file_avg_thermo_data.to_csv( str(lot) + '-' + str(bs) + '_all_molecules_avg_thermo_data.csv', index=False, encoding='utf-8-sig')
	compare_G.to_csv( str(lot) + '-' + str(bs) + '_all_molecules_compare_G(T).csv', index=False, encoding='utf-8-sig')

# CALCULATES RMSD between two molecules
def get_conf_RMS(mol1, mol2, c1, c2, heavy, max_matches_RMSD,log):
	if heavy:
		 mol1 = Chem.RemoveHs(mol1)
		 mol2 = Chem.RemoveHs(mol2)
	rms = Chem.GetBestRMS(mol1,mol2,c1,c2,maxMatches=max_matches_RMSD)
	return rms

# DETECTS INITIAL NUMBER OF SAMPLES AUTOMATICALLY
def auto_sampling(mult_factor,mol,args,log):
	if args.metal_complex:
		if len(args.metal_idx) > 0:
			mult_factor = mult_factor*3*len(args.metal_idx) # this accounts for possible trans/cis isomers in metal complexes
	auto_samples = 0
	auto_samples += 3*(Lipinski.NumRotatableBonds(mol)) # x3, for C3 rotations
	auto_samples += 3*(Lipinski.NHOHCount(mol)) # x3, for OH/NH rotations
	auto_samples += 3*(Lipinski.NumSaturatedRings(mol)) # x3, for boat/chair/envelope confs
	if auto_samples == 0:
		auto_samples = mult_factor
	else:
		auto_samples = mult_factor*auto_samples
	return auto_samples

# DETECTS DIHEDRALS IN THE MOLECULE
def getDihedralMatches(mol, heavy,log):
	#this is rdkit's "strict" pattern
	pattern = r"*~[!$(*#*)&!D1&!$(C(F)(F)F)&!$(C(Cl)(Cl)Cl)&!$(C(Br)(Br)Br)&!$(C([CH3])([CH3])[CH3])&!$([CD3](=[N,O,S])-!@[#7,O,S!D1])&!$([#7,O,S!D1]-!@[CD3]=[N,O,S])&!$([CD3](=[N+])-!@[#7!D1])&!$([#7!D1]-!@[CD3]=[N+])]-!@[!$(*#*)&!D1&!$(C(F)(F)F)&!$(C(Cl)(Cl)Cl)&!$(C(Br)(Br)Br)&!$(C([CH3])([CH3])[CH3])]~*"
	qmol = Chem.MolFromSmarts(pattern)
	matches = mol.GetSubstructMatches(qmol)

	#these are all sets of 4 atoms, uniquify by middle two
	uniqmatches = []
	seen = set()
	for (a,b,c,d) in matches:
		if (b,c) not in seen and (c,b) not in seen:
			if heavy:
				if mol.GetAtomWithIdx(a).GetSymbol() != 'H' and mol.GetAtomWithIdx(d).GetSymbol() != 'H':
					seen.add((b,c))
					uniqmatches.append((a,b,c,d))
			if heavy != True:
				if mol.GetAtomWithIdx(c).GetSymbol() == 'C' and mol.GetAtomWithIdx(d).GetSymbol() == 'H':
					pass
				else:
					seen.add((b,c))
					uniqmatches.append((a,b,c,d))
	return uniqmatches

# IF NOT USING DIHEDRALS, THIS REPLACES I BACK TO THE METAL WHEN METAL = TRUE
# AND WRITES THE RDKIT SDF FILES. WITH DIHEDRALS, IT OPTIMIZES THE ROTAMERS
def genConformer_r(mol, conf, i, matches, degree, sdwriter,args,name,log):
	if i >= len(matches): # base case, torsions should be set in conf
		#setting the metal back instead of I
		if args.metal_complex and args.nodihedrals:
			for atom in mol.GetAtoms():
				if atom.GetIdx() in args.metal_idx:
					re_symbol = args.metal_sym[args.metal_idx.index(atom.GetIdx())]
					atomic_number = possible_atoms.index(re_symbol)
					atom.SetAtomicNum(atomic_number)
		sdwriter.write(mol,conf)
		return 1
	else:
		#log.write(str(i)+'starting new else writing')
		#incr = math.pi*degree / 180.0
		total = 0
		deg = 0
		while deg < 360.0:
			#log.write(matches[i])
			rad = math.pi*deg / 180.0
			rdMolTransforms.SetDihedralRad(mol.GetConformer(conf),*matches[i],value=rad)
			#recalculating energies after rotation
			if args.ff == "MMFF":
				GetFF = Chem.MMFFGetMoleculeForceField(mol, Chem.MMFFGetMoleculeProperties(mol),confId=conf)
			elif args.ff == "UFF":
				GetFF = Chem.UFFGetMoleculeForceField(mol,confId=conf)
			else:
				log.write('   Force field {} not supported!'.format(args.ff))
				sys.exit()
			GetFF.Initialize()
			GetFF.Minimize(maxIts=args.opt_steps_RDKit)
			energy = GetFF.CalcEnergy()
			mol.SetProp("Energy",energy)
			mol.SetProp('_Name',name)
			total += genConformer_r(mol, conf, i+1, matches, degree, sdwriter,args,name,log)
			deg += degree
		return total

# AUTOMATICALLY SETS THE CHARGE FOR METAL COMPLEXES
def rules_get_charge(mol,args,log):
	C_group = ['C', 'Se', 'Ge']
	N_group = ['N', 'P', 'As']
	O_group = ['O', 'S', 'Se']
	Cl_group = ['Cl', 'Br', 'I']

	charge = np.empty(len(args.metal_idx), dtype=int)
	neighbours = []
	#get the neighbours of metal atom
	for atom in mol.GetAtoms():
		if atom.GetIdx() in args.metal_idx:
			charge_idx = args.metal_idx.index(atom.GetIdx())
			neighbours = atom.GetNeighbors()
			charge[charge_idx] = args.m_oxi[charge_idx]

			for atom in neighbours:
				#Carbon list
				if atom.GetSymbol() in C_group:
					if atom.GetTotalValence()== 4:
						charge[charge_idx] = charge[charge_idx] - 1
					if atom.GetTotalValence()== 3:
						charge[charge_idx] = charge[charge_idx] - 0
				#Nitrogen list
				if atom.GetSymbol() in N_group:
					if atom.GetTotalValence() == 3:
						charge[charge_idx] = charge[charge_idx] - 1
					if atom.GetTotalValence() == 4:
						charge[charge_idx] = charge[charge_idx] - 0
				#Oxygen list
				if atom.GetSymbol() in O_group:
					if atom.GetTotalValence() == 2:
						charge[charge_idx] = charge[charge_idx] - 1
					if atom.GetTotalValence() == 3:
						charge[charge_idx] = charge[charge_idx] - 0
				#Halogen list
				if atom.GetSymbol() in Cl_group:
					if atom.GetTotalValence() == 1:
						charge[charge_idx] = charge[charge_idx] - 1
					if atom.GetTotalValence() == 2:
						charge[charge_idx] = charge[charge_idx] - 0

	if len(neighbours) == 0:
		#no update in charge as it is an organic molecule
		return args.charge_default
	else:
		return charge

def embed_conf(mol,initial_confs,args,log,coord_Map,alg_Map, mol_template):
	if coord_Map == None and alg_Map == None and mol_template == None:
		cids = rdDistGeom.EmbedMultipleConfs(mol, initial_confs,ignoreSmoothingFailures=True, randomSeed=args.seed,numThreads = 0)
		if len(cids) == 0 or len(cids) == 1 and initial_confs != 1:
			log.write("o  Normal RDKit embeding process failed, trying to generate conformers with random coordinates (with "+str(initial_confs)+" possibilities)")
			cids = rdDistGeom.EmbedMultipleConfs(mol, initial_confs, randomSeed=args.seed, useRandomCoords=True, boxSizeMult=10.0,ignoreSmoothingFailures=True, numZeroFail=1000, numThreads = 0)
		if args.verbose:
			log.write("o  "+ str(len(cids))+" conformers initially generated")
	# case of embed for templates
	else:
		cids = rdDistGeom.EmbedMultipleConfs(mol, initial_confs, randomSeed=args.seed,ignoreSmoothingFailures=True, coordMap = coord_Map,numThreads = 0)
		if len(cids) == 0 or len(cids) == 1 and initial_confs != 1:
			log.write("o  Normal RDKit embeding process failed, trying to generate conformers with random coordinates (with "+str(initial_confs)+" possibilities)")
			cids = rdDistGeom.EmbedMultipleConfs(mol, initial_confs, randomSeed=args.seed, useRandomCoords=True, boxSizeMult=10.0, numZeroFail=1000,ignoreSmoothingFailures=True, coordMap = coord_Map,numThreads = 0)
		if args.verbose:
			log.write("o  "+ str(len(cids))+" conformers initially generated")

	return cids

def min_after_embed(mol,cids,name,initial_confs,rotmatches,dup_data,dup_data_idx,sdwriter,coord_Map,alg_Map, mol_template,args,log):

	cenergy,outmols = [],[]
	bar = IncrementalBar('o  Minimizing', max = len(cids))
	for i, conf in enumerate(cids):
		if coord_Map == None and alg_Map == None and mol_template == None:
			if args.ff == "MMFF":
				GetFF = Chem.MMFFGetMoleculeForceField(mol, Chem.MMFFGetMoleculeProperties(mol),confId=conf)
			elif args.ff == "UFF":
				GetFF = Chem.UFFGetMoleculeForceField(mol,confId=conf)
			else:
				log.write('   Force field {} not supported!'.format(args.ff))
				sys.exit()

			GetFF.Initialize()
			GetFF.Minimize(maxIts=args.opt_steps_RDKit)
			energy = GetFF.CalcEnergy()
			cenergy.append(GetFF.CalcEnergy())

		#id template realign before doing calculations
		else:
			num_atom_match = mol.GetSubstructMatch(mol_template)
			# Force field parameters
			if args.ff == "MMFF":
				GetFF = lambda mol,confId=conf:Chem.MMFFGetMoleculeForceField(mol,Chem.MMFFGetMoleculeProperties(mol),confId=conf)
			elif args.ff == "UFF":
				GetFF = lambda mol,confId=conf:Chem.UFFGetMoleculeForceField(mol,confId=conf)
			else:
				log.write('   Force field {} not supported!'.format(args.ff))
				sys.exit()
			getForceField=GetFF

			# clean up the conformation
			ff_temp = getForceField(mol, confId=conf)
			for k, idxI in enumerate(num_atom_match):
				for l in range(k + 1, len(num_atom_match)):
					idxJ = num_atom_match[l]
					d = coord_Map[idxI].Distance(coord_Map[idxJ])
					ff_temp.AddDistanceConstraint(idxI, idxJ, d, d, 10000)
			ff_temp.Initialize()
			#reassignned n from 4 to 10 for better embed and minimzation
			n = 10
			more = ff_temp.Minimize()
			while more and n:
				more = ff_temp.Minimize()
				n -= 1
			energy = ff_temp.CalcEnergy()
			# rotate the embedded conformation onto the core_mol:
			rdMolAlign.AlignMol(mol, mol_template,prbCid=conf, atomMap=alg_Map,reflect=True,maxIters=100)
			cenergy.append(energy)

		# outmols is gonna be a list containing "initial_confs" mol objects with "initial_confs"
		# conformers. We do this to SetProp (Name and Energy) to the different conformers
		# and log.write in the SDF file. At the end, since all the mol objects has the same
		# conformers, but the energies are different, we can log.write conformers to SDF files
		# with the energies of the parent mol objects. We measured the computing time and
		# it's the same as using only 1 parent mol object with 10 conformers, but we couldn'temp
		# SetProp correctly
		pmol = PropertyMol.PropertyMol(mol)
		outmols.append(pmol)
		bar.next()
	bar.finish()

	for i, cid in enumerate(cids):
		outmols[cid].SetProp('_Name', name + ' conformer ' + str(i+1))
		outmols[cid].SetProp('Energy', cenergy[cid])

	cids = list(range(len(outmols)))
	sortedcids = sorted(cids,key = lambda cid: cenergy[cid])

	log.write("\n\no  Filters after intial embedding of "+str(initial_confs)+" conformers")
	selectedcids,selectedcids_initial, eng_dup,eng_rms_dup =[],[],-1,-1
	bar = IncrementalBar('o  Filtering based on energy (pre-filter)', max = len(sortedcids))
	for i, conf in enumerate(sortedcids):
		# This keeps track of whether or not your conformer is unique
		excluded_conf = False
		# include the first conformer in the list to start the filtering process
		if i == 0:
			selectedcids_initial.append(conf)
		# check rmsd
		for seenconf in selectedcids_initial:
			E_diff = abs(cenergy[conf] - cenergy[seenconf]) # in kcal/mol
			if E_diff < args.initial_energy_threshold:
				eng_dup += 1
				excluded_conf = True
				break
		if excluded_conf == False:
			if conf not in selectedcids_initial:
				selectedcids_initial.append(conf)
		bar.next()
	bar.finish()


	if args.verbose:
		log.write("o  "+str(eng_dup)+ " Duplicates removed  pre-energy filter (E < "+str(args.initial_energy_threshold)+" kcal/mol)")
	#reduce to unique set
	if args.verbose:
		log.write("o  Removing duplicate conformers (RMSD < "+ str(args.rms_threshold)+ " and E difference < "+str(args.energy_threshold)+" kcal/mol)")

	bar = IncrementalBar('o  Filtering based on energy and RMSD', max = len(selectedcids_initial))
	#check rmsd
	for i, conf in enumerate(selectedcids_initial):

		# #set torsions to same value
		for m in rotmatches:
			rdMolTransforms.SetDihedralDeg(outmols[conf].GetConformer(conf),*m,180.0)

		# This keeps track of whether or not your conformer is unique
		excluded_conf = False
		# include the first conformer in the list to start the filtering process
		if i == 0:
			selectedcids.append(conf)
		# check rmsd
		for seenconf in selectedcids:
			E_diff = abs(cenergy[conf] - cenergy[seenconf]) # in kcal/mol
			if  E_diff < args.energy_threshold:
				rms = get_conf_RMS(outmols[conf],outmols[conf],seenconf,conf, args.heavyonly, args.max_matches_RMSD,log)
				if rms < args.rms_threshold:
					excluded_conf = True
					eng_rms_dup += 1
					break
		if excluded_conf == False:
			if conf not in selectedcids:
				selectedcids.append(conf)
		bar.next()
	bar.finish()

	if args.verbose:
		log.write("o  "+str(eng_rms_dup)+ " Duplicates removed (RMSD < "+str(args.rms_threshold)+" / E < "+str(args.energy_threshold)+" kcal/mol) after rotation")
	if args.verbose:
		log.write("o  "+ str(len(selectedcids))+" unique conformers remain")

	dup_data.at[dup_data_idx, 'RDKit-energy-duplicates'] = eng_dup
	dup_data.at[dup_data_idx, 'RDKit-RMSD-and-energy-duplicates'] = eng_rms_dup
	dup_data.at[dup_data_idx, 'RDKIT-Unique-conformers'] = len(selectedcids)

	#writing charges after RDKIT
	args.charge = rules_get_charge(mol,args,log)
	dup_data.at[dup_data_idx, 'Overall charge'] = np.sum(args.charge)

	# now exhaustively drive torsions of selected conformers
	n_confs = int(len(selectedcids) * (360 / args.degree) ** len(rotmatches))
	if args.verbose and len(rotmatches) != 0:
		log.write("\n\no  Systematic generation of "+ str(n_confs)+ " confomers")
		bar = IncrementalBar('o  Generating conformations based on dihedral rotation', max = len(selectedcids))
	else:
		bar = IncrementalBar('o  Generating conformations', max = len(selectedcids))

	total = 0
	for conf in selectedcids:
		#log.write(outmols[conf])
		total += genConformer_r(outmols[conf], conf, 0, rotmatches, args.degree, sdwriter ,args,outmols[conf].GetProp('_Name'),log)
		bar.next()
	bar.finish()
	if args.verbose and len(rotmatches) != 0:
		log.write("o  %d total conformations generated"%total)
	status = 1

	dup_data.at[dup_data_idx, 'RDKIT-Rotated-conformers'] = total

	return status

def filter_after_rotation(args,name,log,dup_data,dup_data_idx):
	rdmols = Chem.SDMolSupplier(name+'_'+'rdkit'+args.output, removeHs=False)
	if rdmols is None:
		log.write("Could not open "+ name+args.output)
		sys.exit(-1)


	bar = IncrementalBar('o  Filtering based on energy and rms after rotation of dihedrals', max = len(rdmols))
	sdwriter_rd = Chem.SDWriter(name+'_'+'rdkit'+'_'+'rotated'+args.output)

	rd_count = 0
	rd_selectedcids,rd_dup_energy,rd_dup_rms_eng =[],-1,0
	for i, rd_mol_i in enumerate(rdmols):
		mol_rd = Chem.RWMol(rd_mol_i)
		mol_rd.SetProp('_Name',rd_mol_i.GetProp('_Name')+' '+str(i))
		# This keeps track of whether or not your conformer is unique
		excluded_conf = False
		# include the first conformer in the list to start the filtering process
		if rd_count == 0:
			rd_selectedcids.append(rd_mol_i)
			if args.metal_complex:
				for atom in mol_rd.GetAtoms():
					if atom.GetIdx() in args.metal_idx:
						re_symbol = args.metal_sym[args.metal_idx.index(atom.GetIdx())]
						atomic_number = possible_atoms.index(re_symbol)
						atom.SetAtomicNum(atomic_number)
			sdwriter_rd.write(mol_rd)
		# Only the first ID gets included
		rd_count = 1
		# check rmsd
		for rd_mol_j in rd_selectedcids:
			if abs(float(rd_mol_i.GetProp('Energy')) - float(rd_mol_j.GetProp('Energy'))) < args.initial_energy_threshold: # comparison in kcal/mol
				excluded_conf = True
				rd_dup_energy += 1
				break
			if abs(float(rd_mol_i.GetProp('Energy')) - float(rd_mol_j.GetProp('Energy'))) < args.energy_threshold: # in kcal/mol
				rms = get_conf_RMS(mol_rd,rd_mol_j,-1,-1, args.heavyonly, args.max_matches_RMSD,log)
				if rms < args.rms_threshold:
					excluded_conf = True
					rd_dup_rms_eng += 1
					break
		if excluded_conf == False:
			if rd_mol_i not in rd_selectedcids:
				rd_selectedcids.append(rd_mol_i)
				if args.metal_complex:
					for atom in mol_rd.GetAtoms():
						if atom.GetIdx() in args.metal_idx:
							re_symbol = args.metal_sym[args.metal_idx.index(atom.GetIdx())]
							atomic_number = possible_atoms.index(re_symbol)
							atom.SetAtomicNum(atomic_number)
				sdwriter_rd.write(mol_rd)
		bar.next()
	bar.finish()
	sdwriter_rd.close()

	if args.verbose:
		log.write("o  "+str(rd_dup_energy)+ " Duplicates removed initial energy (E < "+str(args.initial_energy_threshold)+" kcal/mol)")
	if args.verbose:
		log.write("o  "+str(rd_dup_rms_eng)+ " Duplicates removed (RMSD < "+str(args.rms_threshold)+" / E < "+str(args.energy_threshold)+" kcal/mol) after rotation")
	if args.verbose:
		log.write("o  "+str(len(rd_selectedcids) )+ " unique conformers remain")

	#filtering process after rotations
	dup_data.at[dup_data_idx, 'RDKIT-Rotated-Unique-conformers'] = len(rd_selectedcids)

	status = 1

	return status

# EMBEDS, OPTIMIZES AND FILTERS RDKIT CONFORMERS
def summ_search(mol, name,args,log,dup_data,dup_data_idx, coord_Map = None,alg_Map=None,mol_template=None):
	sdwriter = Chem.SDWriter(name+'_'+'rdkit'+args.output)

	Chem.SanitizeMol(mol)
	mol = Chem.AddHs(mol)
	mol.SetProp("_Name",name)

	# detects and applies auto-detection of initial number of conformers
	if args.sample == 'auto':
		initial_confs = int(auto_sampling(args.auto_sample,mol,args,log))

	else:
		initial_confs = int(args.sample)

	dup_data.at[dup_data_idx, 'Molecule'] = name

	rotmatches = getDihedralMatches(mol, args.heavyonly,log)
	if len(rotmatches) > args.max_torsions:
		log.write("x  Too many torsions (%d). Skipping %s" %(len(rotmatches),(name+args.output)))
		status = -1

	else:
		dup_data.at[dup_data_idx, 'RDKIT-Initial-samples'] = initial_confs
		if args.nodihedrals == True:
			rotmatches =[]
		cids = embed_conf(mol,initial_confs,args,log,coord_Map,alg_Map, mol_template)
		#energy minimize all to get more realistic results
		#identify the atoms and decide Force Field

		for atom in mol.GetAtoms():
			if atom.GetAtomicNum() > 36: #up to Kr for MMFF, if not the code will use UFF
				args.ff = "UFF"
				#log.write("UFF is used because there are atoms that MMFF doesn't recognise")
		if args.verbose:
			log.write("o  Optimizing "+ str(len(cids))+ " initial conformers with "+ args.ff)
		if args.verbose:
			if args.nodihedrals == False:
				log.write("o  Found "+ str(len(rotmatches))+ " rotatable torsions")
				# for [a,b,c,d] in rotmatches:
				# 	log.write('  '+mol.GetAtomWithIdx(a).GetSymbol()+str(a+1)+ mol.GetAtomWithIdx(b).GetSymbol()+str(b+1)+ mol.GetAtomWithIdx(c).GetSymbol()+str(c+1)+mol.GetAtomWithIdx(d).GetSymbol()+str(d+1))
			else:
				log.write("o  Systematic torsion rotation is set to OFF")

		status = min_after_embed(mol,cids,name,initial_confs,rotmatches,dup_data,dup_data_idx,sdwriter,coord_Map,alg_Map, mol_template,args,log)
	sdwriter.close()

	if status!= -1:
		#getting the energy from and mols after rotations
		if not args.nodihedrals and len(rotmatches) != 0:
			status = filter_after_rotation(args,name,log,dup_data,dup_data_idx)
		elif not args.nodihedrals and len(rotmatches) ==0:
			status = 0

	return status

# xTB AND ANI1 OPTIMIZATIONS
def optimize(mol, args, program,log,dup_data,dup_data_idx):
	# if large system increase stck size
	if args.large_sys:
		os.environ['OMP_STACKSIZE'] = args.STACKSIZE

	# removing the Ba atom if NCI complexes
	if args.nci_complex:
		for atom in mol.GetAtoms():
			if atom.GetSymbol() =='I':
				atom.SetAtomicNum(1)

	if args.metal_complex and args.nodihedrals == False:
		for atom in mol.GetAtoms():
			if atom.GetIdx() in args.metal_idx:
				re_symbol = args.metal_sym[args.metal_idx.index(atom.GetIdx())]
				atomic_number = possible_atoms.index(re_symbol)
				atom.SetAtomicNum(atomic_number)

	elements = ''
	ase_metal = []
	ase_metal_idx = []
	for i,atom in enumerate(mol.GetAtoms()):
		if atom.GetIdx() in args.metal_idx:
			ase_metal.append(i)
			ase_metal_idx.append(atom.GetIdx())
		elements += atom.GetSymbol()

	args.charge = rules_get_charge(mol,args,log)
	dup_data.at[dup_data_idx, 'Overall charge'] = np.sum(args.charge)


	cartesians = mol.GetConformers()[0].GetPositions()

	coordinates = torch.tensor([cartesians.tolist()], requires_grad=True, device=device)

	if program == 'ani':
		species = model.species_to_tensor(elements).to(device).unsqueeze(0)
		_, ani_energy = model((species, coordinates))

		ase_molecule = ase.Atoms(elements, positions=coordinates.tolist()[0], calculator=model.ase())
		### make a function for constraints and optimization
		if args.constraints != None:
			fb = ase.constraints.FixBondLength(0, 1)
			ase_molecule.set_distance(0,1,2.0)
			ase_molecule.set_constraint(fb)

		optimizer = ase.optimize.BFGS(ase_molecule, trajectory='ANI1_opt.traj')
		optimizer.run(fmax=args.opt_fmax, steps=args.opt_steps)
		if len(ase.io.Trajectory('xTB_opt.traj', mode='r')) != (args.opt_steps+1):
			species_coords = ase_molecule.get_positions().tolist()
			coordinates = torch.tensor([species_coords], requires_grad=True, device=device)
			converged = 0
		###############################################################################
		# Now let's compute energy:
		_, ani_energy = model((species, coordinates))
		sqm_energy = ani_energy.item() * hartree_to_kcal # Hartree to kcal/mol
		###############################################################################

	elif program == 'xtb':

		if args.metal_complex:
			#passing charges metal present
			ase_molecule = ase.Atoms(elements, positions=coordinates.tolist()[0],calculator=GFN2()) #define ase molecule using GFN2 Calculator
			if os.path.splitext(args.input)[1] == '.csv' or os.path.splitext(args.input)[1] == '.cdx' or os.path.splitext(args.input)[1] == '.smi':
				for i,atom in enumerate(ase_molecule):
					if i in ase_metal:
						ase_charge = args.charge[args.metal_idx.index(ase_metal_idx[ase_metal.index(i)])]

						#will update only for cdx, smi, and csv formats.
						atom.charge = ase_charge

			else:
				atom.charge = args.charge_default
				if args.verbose:
					log.write('o  The Overall charge is read from the .com file ')
		else:
			ase_molecule = ase.Atoms(elements, positions=coordinates.tolist()[0],calculator=GFN2()) #define ase molecule using GFN2 Calculator
		optimizer = ase.optimize.BFGS(ase_molecule, trajectory='xTB_opt.traj',logfile='xtb.opt')
		optimizer.run(fmax=args.opt_fmax, steps=args.opt_steps)
		if len(ase.io.Trajectory('xTB_opt.traj', mode='r')) != (args.opt_steps+1):
			species_coords = ase_molecule.get_positions().tolist()
			coordinates = torch.tensor([species_coords], requires_grad=True, device=device)
			converged = 0
		###############################################################################
		# Now let's compute energy:
		xtb_energy = ase_molecule.get_potential_energy()
		sqm_energy = (xtb_energy / Hartree)* hartree_to_kcal
		###############################################################################

	else:
		log.write('program not defined!')

	energy, converged, cartesians = sqm_energy, converged, np.array(coordinates.tolist()[0])
	# update coordinates of mol object
	for j in range(mol.GetNumAtoms()):
		[x,y,z] = cartesians[j]
		mol.GetConformer().SetAtomPosition(j,Point3D(x,y,z))

	return mol, converged, energy

# WRITE SDF FILES FOR xTB AND ANI1
def write_confs(conformers, energies, name, args, program,log):
	if len(conformers) > 0:
		# list in energy order
		cids = list(range(len(conformers)))
		sortedcids = sorted(cids, key = lambda cid: energies[cid])

		name = name.split('_rdkit')[0]# a bit hacky
		sdwriter = Chem.SDWriter(name+'_'+program+args.output)

		write_confs = 0
		for cid in sortedcids:
			sdwriter.write(conformers[cid])
			write_confs += 1

		if args.verbose:
			log.write("o  Writing "+str(write_confs)+ " conformers to file " + name+'_'+program+args.output)
		sdwriter.close()
	else:
		log.write("x  No conformers found!")

# xTB AND ANI1 OPTIMIZATION, FILTER AND WRITING SDF FILES
def mult_min(name, args, program,log,dup_data,dup_data_idx):
	inmols = Chem.SDMolSupplier(name+args.output, removeHs=False)
	if inmols is None:
		log.write("Could not open "+ name+args.output)
		sys.exit(-1)

	globmin, n_high,n_dup_energy, n_dup_rms_eng  = None, 0, 0, 0
	c_converged, c_energy, outmols = [], [], []

	if args.verbose:
		log.write("\n\no  Multiple minimization of "+ name+args.output+ " with "+ program)
	bar = IncrementalBar('o  Minimizing', max = len(inmols))

	for i,mol in enumerate(inmols):
		bar.next()
		conf = 1
		if mol is not None:
			# optimize this structure and record the energy
			mol, converged, energy = optimize(mol, args, program,log,dup_data,dup_data_idx)

			if globmin == None:
				globmin = energy
			if energy < globmin:
				globmin = energy

			if converged == 0 and abs(energy - globmin) < args.ewin: # comparison in kcal/mol
				unique = 0

				# compare against all previous conformers located
				for j,seenmol in enumerate(outmols):
					if abs(energy - c_energy[j]) < args.initial_energy_threshold: # comparison in kcal/mol
						unique += 1
						n_dup_energy += 1
						break

					if abs(energy - c_energy[j]) < args.energy_threshold: # comparison in kcal/mol
						rms = get_conf_RMS(mol, seenmol, 0, 0, args.heavyonly, args.max_matches_RMSD,log)
						if rms < args.rms_threshold:
							unique += 1
							n_dup_rms_eng += 1
							break

				if unique == 0:
					pmol = PropertyMol.PropertyMol(mol)
					outmols.append(pmol)
					c_converged.append(converged)
					c_energy.append(energy)
					conf += 1
			else:
				n_high += 1
		else:
			pass #log.write("No molecules to optimize")

	bar.finish()
	if args.verbose:
		log.write("o  "+str( n_dup_energy)+ " Duplicates removed initial energy (E < "+str(args.initial_energy_threshold)+" kcal/mol)")
	if args.verbose:
		log.write("o  "+str( n_dup_rms_eng)+ " Duplicates removed (RMSD < "+str(args.rms_threshold)+" / E < "+str(args.energy_threshold)+" kcal/mol)")
	if args.verbose:
		log.write("o  "+str( n_high)+ " Conformers rejected based on energy (E > "+str(args.ewin)+" kcal/mol)")

	# if SQM energy exists, overwrite RDKIT energies and geometries
	cids = list(range(len(outmols)))
	sortedcids = sorted(cids, key = lambda cid: c_energy[cid])

	name_mol = name.split('_rdkit')[0]

	for i, cid in enumerate(sortedcids):
		outmols[cid].SetProp('_Name', name_mol +' conformer ' + str(i+1))
		outmols[cid].SetProp('Energy', c_energy[cid])

	if program == 'xtb':
		dup_data.at[dup_data_idx, 'xTB-Initial-samples'] = len(inmols)
		dup_data.at[dup_data_idx, 'xTB-initial_energy_threshold'] = n_dup_energy
		dup_data.at[dup_data_idx, 'xTB-RMSD-and-energy-duplicates'] = n_dup_rms_eng
		dup_data.at[dup_data_idx, 'xTB-Unique-conformers'] = len(sortedcids)

	if program == 'ani':
		dup_data.at[dup_data_idx, 'ANI1ccx-Initial-samples'] = len(inmols)
		dup_data.at[dup_data_idx, 'ANI1ccx-initial_energy_threshold'] = n_dup_energy
		dup_data.at[dup_data_idx, 'ANI1ccx-RMSD-and-energy-duplicates'] = n_dup_rms_eng
		dup_data.at[dup_data_idx, 'ANI1ccx-Unique-conformers'] = len(sortedcids)

	# write the filtered, ordered conformers to external file

	write_confs(outmols, c_energy, name, args, program,log)
