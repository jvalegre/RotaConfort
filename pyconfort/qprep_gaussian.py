#!/usr/bin/env python

#########################################################.
# 		   This file stores all the functions 		    #
# 	       used in writing SDF and COM files,           #
#              as well as the logger and                #
#                 yaml file importer		            #
#########################################################.

import subprocess
import glob
import re
from operator import itemgetter
from itertools import groupby
from pathlib import Path
import pandas as pd
import rdkit
from pyconfort.utils import periodic_table
from pyconfort.turbomole import TurbomoleInput

try:
    import pybel
except ImportError:
    from openbabel import pybel



# Hotfixes
def fix_obabel_isotopes(gjf_lines):
	"""
	Ensures that gaussian input lines with isotopes ('H  (Iso=2)  x  y  z')
	have the appropiate format for gaussian inputs ('H(Iso=2)  x  y  z'). 
	Modifies in-place the input list.

	Parameters
	----------
	gjf_lines : list
		list of strings corresponding to a gaussian input file
	"""
	for i,line in enumerate(gjf_lines):
		if '(Iso' in line:
			assert len(line.split()) == 5
			gjf_lines[i] = ''.join(line.split(maxsplit=1))

# Basis set class
class BasisSet(object):
	"""
	Representation of the neccesary information related with basis sets. May 
	contain information about auxiliary basis sets and ECPs. 

	Parameters
	----------
	basis : dict, optional
		dictionary with element symbols as keys and their corresponding basis 
		set as value. 'all' and 'default' are accepted as keys, by default None
	auxbasis : dict, optional
		dictionary with element symbols as keys and their corresponding auxiliary 
		basis set as value. 'all' and 'default' are accepted as keys, by default 
		None
	ecp : dict, optional
		dictionary with element symbols as keys and their corresponding ECP 
		as value. 'all' and 'default' are not accepted as keys, by default None.
	"""
	_counter = 0

	def __init__(self,basis=None,auxbasis=None,ecp=None,name=None):
		self.basis = basis
		if basis is None: 
			self._basis = None
		else: 
			self._basis = dict()
			self._basis.update(self.basis)
		self.auxbasis = auxbasis
		if auxbasis is None: 
			self._auxbasis = None
		else: 
			self._auxbasis = dict()
			self._auxbasis.update(self.auxbasis)
		self.elements = set()
		self._elements = set() # Hardcopy to allow reset behaviour
		reserved_keys = ['all','default']
		if not(ecp is None) and any(key in reserved_keys for key in ecp): 
			raise ValueError("'all' or 'default' key found in the ecp parameter")
		self.ecp = ecp
		items = [basis,auxbasis,ecp]
		for item in items:
			if item is None:
				continue 
			keys = [key for key in item if key not in reserved_keys] 
			self.elements.update(keys)
			self._elements.update(keys)
		if name is None:
			default_name = f'basisset_{self._counter:02d}'
			name = self.basis('all','') or self.basis('default','')
			if not name: 
				name = default_name
				self._counter += 1
		self.name = self._homogenize_name(name)

	def _homogenize_name(self,name):
		"""
		Ensures that the name of the basis set can be used as a folder name. 

		Parameters
		----------
		name : str
			initialized name

		Returns
		-------
		str
			modified name
		"""
		if name.find('**') > -1:
			name = name.replace('**','(d,p)')
		elif name.find('*') > -1:
			name = name.replace('*','(d)')

		if str(name).find('/') > -1: 
			new_name =  str(name).split('/')[0]
		else:
			new_name = name
		return new_name

	def update_atomtypes(self,molecules):
		"""
		Updates the elements of the basisset with an iterable of molecules.

		Parameters
		----------
		molecules : list
			list of RDKit Molecule objects
		"""
		elements = set()
		for molecule in molecules: 
			if isinstance(molecule,rdkit.Chem.rdchem.Mol): 
				atoms = [atom for atom in molecule.GetAtoms()]
				syms = [atom.GetSymbol() for atom in atoms]
			elif isinstance(molecule,pybel.Molecule):
				atoms = [atom for atom in molecule.atoms]
				atnums = [atom.OBAtom.GetAtomicNum() for atom in atoms]
				syms = [periodic_table[atnum] for atnum in atnums]
			else:
				raise ValueError(f'{molecule.__class__} is not a valid molecule object')
			elements.update(syms)
		self.elements.update(elements)
		# Now update the basis,auxbasis and ecp dictionaries
		for element in elements:
			for item in [self.basis,self.auxbasis]: 
				if item is None:
					continue
				val = item.get(element,'') or item.get('default','') or item.get('all','')
				item[element] = val
		
	def clear_atomtypes(self): 
		"""
		Resets the state of the Basisset to its initialization state.

		Parameters
		----------
		molecules : list
			list of RDKit Molecule objects
		"""
		self.elements = set()
		self.elements.update(self._elements)
		for attr in ['basis','auxbasis']:
			val = getattr(self,attr) 
			if val is None:
				continue
			backup = getattr(self,f'_{attr}')
			new_val = dict()
			new_val.update(backup)
			setattr(self,attr,new_val)
		
	def write_basisfile(self,filepath):
		"""
		Writes a basis set file that can be read back into a basis set object.

		Parameters
		----------
		filepath : str or Path
			path to the desired basis set file. 
		"""
		lines = []
		for attr in ['basis','auxbasis','ecp']:
			mappable = getattr(self,attr)
			if mappable is None: 
				continue
			lines.append(f'${attr}')
			k_all = mappable.get('all',None)
			k_default = mappable.get('default',None)
			if k_all is not None:
				value = k_all
				lines.append(f'all {value}')
			elif k_default is not None:
				value = k_default
				lines.append(f'default {value}')
			for element in self.elements:
				item = mappable.get(element,value)
				lines.append(f'{element} {item}')
		lines.append('$end')
		with open(filepath,'w') as F:
			F.write('\n'.join(lines))

	@classmethod
	def from_file(cls,filepath):
		"""
		Reads a file containing information on basis sets, auxiliar basis sets and 
		ECPs. The file follows the following format: 
		$basis
		sym1 basis1
		sym2 basis2
		...
		$auxbasis
		sym1 auxbasis1
		sym2 auxbasis2
		...
		$ecp
		sym1 ecp1
		sym2 ecp2
		...
		$end

		Parameters
		----------
		filepath : str or Path
			a valid path to a file with the previously specified format.

		Returns
		-------
		dict or None
			basis, auxbasis, ecp
		"""
		regex = r'\$([^\$]*)'
		regex = re.compile(regex)
		name = Path(filepath).stem
		with open(filepath,'r') as F: 
			txt = F.read()
		keywords = dict()
		kwblocks = regex.findall(txt)
		for block in kwblocks: 
			lines = [line for line in block.split('\n') if line]
			kw_line = lines[0]
			keyword = kw_line.split(' ')[0]
			if keyword == 'end':
				continue
			keywords[keyword] = dict()
			for line in lines[1:]:
				sym,basis = line.split(' ',1)
				keywords[keyword][sym] = basis.strip()
		basis = keywords.get('basis',None)
		auxbasis = keywords.get('auxbasis',None)
		ecp = keywords.get('ecp',None)
		return cls(basis,auxbasis,ecp,name)

# template classes
class GaussianTemplate(object): 
	def __init__(self,basisset=None,functional=None,memory='24GB',nprocs=12,
				commandline=None,solvation='gas_phase',solvent='',
				max_opt_cycles=500,dispersion=None,enable_chk=False, 
				optimization=True,frequencies=True,calcfc=False,
				last_line_for_input=''): 
		self.basisset = basisset
		self.functional = functional
		#Link0
		self.enable_chk = enable_chk
		self.memory = memory
		self.nprocs = nprocs
		# opt options
		self.optimization = optimization
		self.calcfc = calcfc
		self.max_opt_cycles = max_opt_cycles
		# freq options
		self.frequencies = frequencies
		# scrf options
		self.solvation = solvation
		self.solvent = solvent
		# dispersion
		if dispersion is None: 
			dispersion = ''
		self.dispersion = dispersion
		# other commands
		if commandline is None:
			commandline = ''
		self._commandline = commandline
		# other tail
		self.last_line_for_input = last_line_for_input

	def to_dict(self):
		kwargs = dict()
		kwargs['functional'] = self.functional
		if self.basisset is not None: 
			kwargs['basis'] = self.basisset.basis
			kwargs['auxbasis'] = self.basisset.auxbasis
			kwargs['ecp'] = self.basisset.ecp
			
		kwargs['memory'] = self.memory
		kwargs['nprocs'] = self.nprocs
		kwargs['extra_input'] = self.extra_input
		kwargs['enable_chk'] = self.enable_chk
		kwargs['frequencies'] = self.frequencies
		kwargs['dispersion'] = self.dispersion
		kwargs['calcfc'] = self.calcfc
		kwargs['solvation'] = self.solvation
		kwargs['solvent'] = self.solvent
		kwargs['last_line_for_input'] = self.last_line_for_input
		kwargs['max_opt_cycles'] = self.max_opt_cycles
		return kwargs

	@property
	def genecp(self):
		ecp_genecp_atoms = self.basisset.ecp is not None
		ecp_gen_atoms = bool(self.basisset.elements)
		if ecp_genecp_atoms:
			return 'genecp'
		elif ecp_gen_atoms:
			return 'gen'
		else:
			return ''
	@property
	def basis(self):
		if self.genecp:
			return self.genecp
		basis_all = self.basisset.basis.get('all','')
		if basis_all:
			return basis_all
		basis_default = self.basisset.basis.get('default','')
		if basis_default:
			return basis_default
		raise RuntimeError("""Could not determine basis keyword: 
		No 'all' nor 'default' basis set specified and no element specified""")
	
	@property
	def commandline(self): 
		if self._commandline:
			return self._commandline
		return self.get_commandline()

	def get_commandline(self):
		opt_k = ''
		if self.optimization: 
			opt_sub = f'(maxcycles={self.max_opt_cycles}'
			if self.calcfc:
				opt_sub += ',calcfc'
			opt_sub += ')'
			opt_k = f'opt={opt_sub}'
		freq_k = ''
		if self.frequencies: 
			freq_k = 'freq=noraman'
		disp_k = ''
		if self.dispersion:
			disp_k = f'empiricaldispersion={self.dispersion}'
		scrf_k = ''
		if self.solvation != 'gas_phase': 
			scrf_k = f'scrf=({self.solvation},solvent={self.solvent})'
		commandline = f'{self.functional} {self.basis} {opt_k} {freq_k} {disp_k} {scrf_k}'
		return ' '.join(commandline.split())

	@classmethod
	def from_args(cls,args):
		new = cls()

		# Basis set creation
		new.genecp_atoms_sp = args.genecp_atoms_sp
		new.gen_atoms_sp = args.gen_atoms_sp
		new.genecp_atoms = args.genecp_atoms
		new.gen_atoms = args.gen_atoms
		
		#Standard stuff
		new.memory = args.mem
		new.nprocs = args.nprocs
		new.enable_chk = args.chk
		new.extra_input = args.set_input_line
		new.frequencies = args.frequencies
		if args.empirical_dispersion != None: 
			new.dispersion = args.empirical_dispersion
		new.calcfc = args.calcfc
		new.solvation = args.solvent_model
		new.solvent = args.solvent_name
		new.last_line_of_input = args.last_line_for_input
		new.max_opt_cycles = args.max_cycle_opt
		return new

	def get_header(self,filename='',title=''):
		txt = ''
		#Link0
		if self.enable_chk: 
			txt += f'%chk={filename}.chk\n'
		txt += f'%nprocshared={self.nprocs}\n'
		txt += f'%mem={self.memory}\n'
		txt += f'# {self.commandline}'
		return txt
	def get_tail(self):
		txt = ''
		# write basis set section
		basisset = self.basisset.basis
		if self.genecp:
			def_basis = basisset.get('all','')
			def_basis = basisset.get('default',def_basis)
			items = [(sym,basisset.get(sym,def_basis)) for sym in self.basisset.elements]
			items = sorted(items,key=itemgetter(1))
			for basis,pairs in groupby(items,key=itemgetter(1)):
				elements = ' '.join([f'-{sym}' for sym,_ in pairs])
				txt += f'{elements} 0\n{basis}\n****\n'
			txt += '\n'
		# write ecp section
		if self.genecp == 'genecp': 
			items = sorted(list(self.basisset.ecp.items()),key=itemgetter(1))
			for basis,pairs in groupby(items,key=itemgetter(1)):
				elements = ' '.join([f'-{sym}' for sym,_ in pairs])
				txt += f'{elements} 0\n{basis}\n****\n'
			txt += '\n'
		if self.last_line_for_input: 
			txt += f'{self.last_line_for_input}\n'
		txt += '\n'
		return txt
	def write(self,destination,molecule): 
		stem = molecule.title.lstrip().replace(' ','_')
		comfile = f'{destination}/{stem}.com'
		
		header = self.get_header(filename=stem)

		lines = molecule.write('gjf',opt=dict(k=header)).split('\n')
		fix_obabel_isotopes(lines)
		tail = self.get_tail()
		lines.append(tail)
		with open(comfile,'w') as F:
			F.write('\n'.join(lines))

		return comfile

class OrcaTemplate(object):
	"""
	[summary]

	Parameters
	----------
	basisset : [type], optional
		[description], by default None
	functional : [type], optional
		[description], by default None
	memory : str, optional
		[description], by default '24GB'
	nprocs : int, optional
		[description], by default 12
	extra_commandline : [type], optional
		[description], by default None
	solvation : str, optional
		[description], by default 'gas_phase'
	solvent : str, optional
		[description], by default ''
	extra_cpcm_input : [type], optional
		[description], by default None
	scf_iters : int, optional
		[description], by default 500
	mdci : list, optional
		additional input for the MDCI (Matrix driven correlation) section of
		ORCA input, by default None
	print_mini : bool, optional
		[description], by default True
	"""

	def __init__(self,basisset=None,functional=None,memory='24GB',nprocs=12,
				extra_commandline=None,solvation='gas_phase',solvent='',
				extra_cpcm_input=None,scf_iters=500,mdci=None,
				print_mini=True):
		self.basisset = basisset
		self.functional = functional
		# calculate memory for ORCA input
		mem_orca = int(memory[:-2])
		is_GB = 'gb' in memory.lower() 
		if is_GB:
			mem_orca *= 1000
		else:
			# assume MB
			pass
		self.memory = mem_orca # in MB
		self.nprocs = nprocs
		if extra_commandline is None: 
			extra_commandline = ''
		self.extra_commandline = extra_commandline
		self.solvation = solvation
		self.solvent = solvent
		if extra_cpcm_input is None: 
			extra_cpcm_input = []
		self.extra_cpcm_input = extra_cpcm_input
		self.scf_iters = scf_iters
		if mdci is None: 
			mdci = ['Density None']
		self.mdci = mdci
		self.print_mini = print_mini

	def to_dict(self):
		kwargs = dict()
		kwargs['functional'] = self.functional
		if self.basisset is not None: 
			kwargs['basis'] = self.basisset.basis
			kwargs['auxbasis'] = self.basisset.auxbasis
			kwargs['ecp'] = self.basisset.ecp
	
		kwargs['ecp_list'] = self.aux_atoms_orca
		kwargs['bs_gcp'] = self.aux_basis_set_genecp_atoms
		kwargs['bs_gcp_fit'] = self.aux_fit_genecp_atoms
		kwargs['orca_aux_section'] = self.enable_aux_section
		kwargs['memory'] = self.memory
		kwargs['nprocs'] = self.nprocs
		kwargs['extra_input'] = self.extra_input
		kwargs['solvation'] = self.solvation
		kwargs['solvent'] = self.solvent
		kwargs['cpcm_input_orca'] = self.cpcm_input_orca
		kwargs['scf_iters_orca'] = self.scf_iters_orca
		kwargs['orca_mdci'] = self.mdci_orca
		kwargs['print_mini'] = self.print_mini

		return kwargs

	@property
	def enable_aux_section(self):
		return bool(self.basisset.elements) or (self.basisset.ecp is not None)
	@property
	def basis(self):
		if self.enable_aux_section:
			return self.basisset.basis.get('default','')
		basis_all = self.basisset.basis.get('all','')
		if basis_all:
			return basis_all
		raise RuntimeError("Could not determine the basis")

	@classmethod
	def from_args(cls,args):
		new = cls()
		# Standard stuff
		new.memory = args.mem
		new.nprocs = args.nprocs
		new.extra_commandline = args.set_input_line 
		new.solvation = args.solvent_model
		new.solvent = args.solvent_name
		new.extra_cpcm_input = args.cpcm_input
		new.scf_iters = args.orca_scf_iters
		new.mdci = args.mdci_orca
		new.print_mini = args.print_mini_orca

		return new

	def get_aux_section(self):
		txt = '%basis\n'
		# basis set block
		def_basis = self.basis
		items = []
		for sym in self.basisset.elements: 
			basis = self.basisset.basis.get(sym,'')
			if basis and basis == def_basis: 
				continue
			items.append((sym,basis))
		if items: 
			items = sorted(items,key=itemgetter(1))
			for basis,pairs in groupby(items,key=itemgetter(1)):
				elements = ' '.join([f'{sym}' for sym,_ in pairs])
				txt += f'NewGTO {elements} {basis} end\n'
		# Auxiliary Basis set block
		# TODO
		if self.basisset.ecp is None: 
			txt += 'end'
			return txt
		# ECP block
		items = []
		for sym in self.basisset.ecp: 
			ecp = self.basisset.ecp.get(sym,'')
			if basis and basis == def_basis: 
				continue
			items.append((sym,ecp))
		if items: 
			items = sorted(items,key=itemgetter(1))
			for ecp,pairs in groupby(items,key=itemgetter(1)):
				elements = ' '.join([f'{sym}' for sym,_ in pairs])
				txt += f'NewECP {elements} {ecp} end\n'
		txt += 'end'
		return txt
	def get_solvation_section(self):
		txt = ''
		if self.solvation.lower() == 'smd':
			txt += '%cpcm\n'
			txt += 'smd true\n'
			txt += f'SMDsolvent "{self.solvent}"\n'
		elif self.solvation.lower() == 'cpcm':
			txt += f'! CPCM({self.solvent})\n'
			if self.cpcm_input_orca != 'None':
				txt += '%cpcm\n'
				for cpcm_line in self.cpcm_input_orca:
					txt += f'{cpcm_line}\n'
		txt += 'end'
		return txt
	def get_command_line(self):
		commandline = ' '.join(f'{self.basis} {self.functional}'.split())
		if self.extra_commandline != 'None':
			commandline += f' {self.extra_commandline}'
		return commandline

	def get_header(self,title):
		txt =  f'# {title}\n'
		txt +=  '# Memory per core\n'
		txt += f'%maxcore {self.memory}\n'
		txt +=  '# Number of processors\n'
		txt += f'%pal nprocs {self.nprocs} end\n'
		txt += f'! {self.get_command_line()}\n'

		sections = []
		if self.enable_aux_section:
			sections.append(self.get_aux_section())

		if self.solvation != 'gas_phase':
			sections.append(self.get_solvation_section())
		
		sections.append(f'%scf maxiter {self.scf_iters}\nend')

		if self.mdci:
			mdci_lines = ['% mdci',] + self.mdci + ['end',]
			sections.append('\n'.join(mdci_lines))
		
		if self.print_mini:
			mini_lines = [  '%output',
							'printlevel mini',
							'print[ P_SCFInfo ] 1',
							'print[ P_SCFIterInfo ] 1',
							'print[ P_OrbEn ] 0',
							'print[ P_Cartesian ] 0',
							'end',
							'%elprop',
							'Dipole False',
							'end']
			sections.append('\n'.join(mini_lines))
		txt += '\n'.join(sections)
		txt += '\n'
		return txt
	def write(self,destination,molecule):
		stem = molecule.title.lstrip().replace(' ','_')
		infile = f'{destination}/{stem}.inp'
		header = self.get_header(molecule.title)
		xyz_lines = molecule.write('orcainp').split('\n')[3:]
		
		with open(infile,'w') as F: 
			F.write(header)
			F.write('\n'.join(xyz_lines))

		return infile

class TurbomoleTemplate(object):
	def __init__(self,basisset=None,functional=None,dispersion='off',
				grid='m4',epsilon='gas',maxcore=200,ricore=200,cavity='none'): 
		self.basisset = basisset
		self.functional = functional
		self.dispersion =  dispersion
		self.grid =  grid
		self.epsilon =  epsilon
		self.maxcore = maxcore
		self.ricore = ricore
		self.cavity =  cavity
	
	def to_dict(self):
		kwargs = dict()
		kwargs['functional'] = self.functional
		if self.basisset is not None: 
			kwargs['basis'] = self.basisset.basis
			kwargs['auxbasis'] = self.basisset.auxbasis
			kwargs['ecp'] = self.basisset.ecp
			
		kwargs['dispersion'] = self.dispersion
		kwargs['grid'] = self.grid
		kwargs['epsilon'] = self.epsilon
		kwargs['maxcore'] = self.maxcore
		kwargs['ricore'] = self.ricore
		kwargs['cavity'] = self.cavity
		return kwargs

	@classmethod
	def from_args(cls,args):
		new = cls()
		new.dispersion = args.tmdispersion
		new.grid = args.tmgrid
		new.epsilon = args.tmepsilon
		new.maxcore = args.tmmaxcore
		new.ricore = args.tmricore
		new.cavity = args.tmcavity

		return new
	def write(self,destination,molecule): 
		name,i = molecule.title.strip().rsplit(maxsplit=1)
		stem = f'{name}_{i}'
		folder = Path(f'{destination}/{stem}')
		assert folder.parent.exists()
		folder.mkdir(exist_ok=True,parents=False)
		xyz_file = str(folder/f'{stem}.xyz')  
		molecule.write('xyz',xyz_file)
		coord_file = str(folder/f'coord')
		molecule.write('tmol',coord_file)
		kwargs = self.to_dict()
		t_input = TurbomoleInput(folder,charge=molecule.charge, multiplicity=molecule.spin,
		title=molecule.title,**kwargs)
		t_input.generate()
		return folder

# Aux Functions for QM input generation	
def get_molecule_list(filepath,lowest_only=False,
						lowest_n=False, energy_threshold=0.0):
	out_molecules = []
	
	molecules = [mol for mol in pybel.readfile('sdf',filepath)]
	energies = [mol.energy for mol in molecules]
	min_energy = energies[0]
	for mol,energy in zip(molecules,energies):
		is_in_threshold = energy - min_energy < energy_threshold
		title,i = mol.title.strip().rsplit(maxsplit=1) 
		mol.title = f"{title} {int(i):03d}"
		if lowest_n and is_in_threshold:
			out_molecules.append(mol)
		elif lowest_n:
			break
		elif lowest_only:
			out_molecules.append(mol)
			break
		else:
			out_molecules.append(mol)

	return out_molecules

def get_basisset_list(args,option='opt'): 
	if option=='opt':
		if args.basis_sets: 
			return [BasisSet({'all':bs}) for bs in args.basis_sets]
		elif args.basisfiles: 
			return [BasisSet.from_file(file) for file in args.basisfiles]
	elif option=='sp': 
		if args.basis_sets_sp: 
			return [BasisSet({'all':bs}) for bs in args.basis_sets_sp]
		elif args.basisfiles_sp: 
			return [BasisSet.from_file(file) for file in args.basisfiles_sp]
	return []

# MAIN FUNCTION TO CREATE QM jobs
def write_qm_input_files(destination, template, molecules, charge_data, mult='auto'):
	qm_files = []
	for mol in molecules:

		molname = mol.title.strip().rsplit(maxsplit=1)

		# Get its charge and set it
		found_charges = charge_data.query(f'Molecule=="{molname}"')['Overall charge'].tolist()
		if not found_charges: # not in the dataframe
			charge = mol.data['Real charge']
		else:
			charge = found_charges[0]
		
		if charge == 'Invalid':
			continue
		
		mol.OBMol.SetTotalCharge(int(charge))
		# Set multiplicity
		if mult != 'auto':
			mol.OBMol.SetTotalSpinMultiplicity(int(mult))

		newfile = template.write(destination,mol)
		
		qm_files.append(newfile)

def load_charge_data(filepath,backup_files):
	#read in dup_data to get the overall charge of MOLECULES
	invalid_files = []
	try:
		charge_data = pd.read_csv(filepath, usecols=['Molecule','Overall charge'])
	except:
		charge_data = pd.DataFrame()
		for i,sdf_file in enumerate(backup_files):
			if not(Path(sdf_file).exists()):
				invalid_files.append(sdf_file)
				maxsplit = 1
				if 'filter' in sdf_file: 
					maxsplit += 1
				name = sdf_file.rsplit('_',maxsplit[0])
				charge = 'Invalid'
			else:
				mol = next(pybel.readfile(sdf_file))
				name = mol.title.split(maxsplit=1)[0]
				charge = mol.data['Real charge']
			charge_data.at[i,'Molecule'] = name
			charge_data.at[i,'Overall charge'] = charge
	return charge_data,invalid_files

# MAIN QPREP FUNCTION
def qprep_main(w_dir_initial,args,log):

	if len(args.exp_rules) >= 1:
		conf_files =  glob.glob('*_rules.sdf')
	# define the SDF files to convert to COM Gaussian files
	elif args.CMIN == 'xtb': 
		conf_files =  glob.glob('*_xtb.sdf')
	elif args.CMIN=='ani':
		conf_files =  glob.glob('*_ani.sdf')
	elif args.CSEARCH=='rdkit':
		conf_files =  glob.glob('*_rdkit.sdf')
	elif args.CSEARCH=='summ':
		conf_files =  glob.glob('*_summ.sdf')
	elif args.CSEARCH=='fullmonte':
		conf_files =  glob.glob('*_fullmonte.sdf')
	else:
		conf_files =  glob.glob('*.sdf')

	if args.com_from_xyz:
		xyz_files =  glob.glob('*.xyz')
		for file in xyz_files:
			mol = next(pybel.readfile('xyz',file))
			stem = Path(file).stem
			mol.write('sdf',f'{stem}.sdf')
		conf_files =  glob.glob('*.sdf')

	if not conf_files: 
		log.write('\nx  No SDF files detected to convert to gaussian COM files')
		return 

	# names for directories created
	if args.QPREP == 'gaussian':
		qm_folder = Path(f'{w_dir_initial}/QMCALC/G16')
		template = GaussianTemplate.from_args(args)
	elif args.QPREP == 'orca':
		qm_folder = Path(f'{w_dir_initial}/QMCALC/ORCA')
		template = OrcaTemplate.from_args(args)
	elif args.QPREP == 'turbomole':
		qm_folder = Path(f'{w_dir_initial}/QMCALC/TURBOMOLE')
		template = TurbomoleTemplate.from_args(args)

	csv_name = args.input.split('.')[0]
	csv_file = f"{w_dir_initial}/CSEARCH/csv_files/{csv_name}-CSEARCH-Data.csv"
	charge_data, invalid_files = load_charge_data(csv_file,conf_files)

	# remove the invalid files and non-existing files
	accept_file = lambda x: x not in invalid_files and Path(x).exists()
	conf_files = [file for file in conf_files if accept_file(file) ]
	
	# Prepare the list of molecules that are to be written 
	molecules = []
	for file in conf_files:
		filepath = f'{w_dir_initial}/{file}'
		new_mols = get_molecule_list(filepath,
							lowest_only=args.lowest_only,lowest_n=args.lowest_n,
							energy_threshold=args.energy_threshold_for_gaussian)
		molecules.extend(new_mols)
	
	basisset_list = get_basisset_list(args,'opt')

	# Update each basis set to include the elements of all the molecules
	for bs in basisset_list: 
		bs.update_atomtypes(molecules)

	# Ensure a matching length of theory and basis set
	if len(args.level_of_theory) == 1:
		items = [(args.level_of_theory[0],bs) for bs in basisset_list]
	elif len(basisset_list) == 1:
		items = [(func,basisset_list[0]) for func in args.level_of_theory]
	elif len(basisset_list) == len(args.level_of_theory): 
		items = [(func,bs) for func,bs in zip(args.level_of_theory,basisset_list)]
	else:
		raise ValueError('Inconsistent size of basis sets and theory level')
	
	for functional,basisset in items:
		folder = qm_folder/f'{functional}-{basisset.name}'
		log.write(f"\no  Preparing QM input files in {folder}")

		template.functional = functional
		template.basisset = basisset

		# this variable keeps track of folder creation
		folder.mkdir(parents=True,exist_ok=True)

		# writing the com files
		# check conf_file exists, parse energies and then write DFT input
		qm_files = write_qm_input_files(folder, template, molecules,
										charge_data, mult=args.mult)
		
		# submitting the input file on a HPC
		if args.qsub:
			for qm_file in qm_files: 
				cmd_qsub = [args.submission_command, qm_file]
				subprocess.call(cmd_qsub)
