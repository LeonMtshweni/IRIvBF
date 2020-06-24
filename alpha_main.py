#!/usr/bin/env python3
import os, sys
from os import path
import beta_setup as beta
import glob
import shutil

#---------------------------------------------------------------------------------------
# path to remember
cwd = os.getcwd()
# crease essential directories to keep products
beta.create_dirs()
IDIA_CONTAINER_PATH = '/software/astro/caracal/STIMELA_IMAGES_1.6.1/'
STIMELA_CONTAINER_PATH = '/software/astro/caracal/STIMELA_IMAGES_1.6.1/'
#wsclean container
WSCLEAN_CONTAINER = STIMELA_CONTAINER_PATH +'stimela_wsclean_1.6.0.sif'
# casa container
CASA_CONTAINER = '/idia/software/containers/casa-stable-4.7.2.simg'
# python container
PYTHON_CONTAINER = '/idia/software/containers/python3/python3-2020-01-28.simg'
# source finding container
SOURCE_FINDING_CONTAINER = '/idia/software/containers/sourcefinding-dev-2019-09-23.simg'
# directory where data is fetched
MS_BAK_DIR = '/scratch/users/mtshweni/masters/msback_up/'
# mask directory
MASK_DIR = '/scratch/users/mtshweni/masters/masks/'

# Essential directories
LOGS      = cwd + '/logs'
MAPS      = cwd + '/maps'
SCRIPTS   = cwd + '/scripts'
MS_DIR    = cwd + '/ms_files'
BDSF      = cwd + '/bdsf' 
IMG_STATS = cwd + '/image_stats'
#---------------------------------------------------------------------------------------

def main():

    # name of the submit file
    submit_file = 'submit_jobs.sh'

    # Open file for writing
    f = open(submit_file,'w')

    # write header information
    f.write('#!/bin/bash\n')

    # load the list of data to be copied
    mslist = sys.argv[1].split(',')

    # list of uvrange values
    uvlist = sys.argv[2].split(',')

    # list of fits masks
    masklist = sys.argv[3].split(',')

    # list of minivw
    wsclean_uv_range = sys.argv[4].split(',')
    
    #pybdsf selection parameters
    isl_pix_input = sys.argv[5].split(',') 

    # this is the data to be copied
    og_dat = sys.argv[6]

    # ms_file to be copied
    ms_path = MS_BAK_DIR + og_dat
    
    # this loop simultaneously iterates through the lists provided
    for (myms,uv_range,fitsmask,min_uvw,isl_pix) in zip(mslist,uvlist,masklist,wsclean_uv_range,isl_pix_input):

         #image names 
         blind_prefix = MAPS  + '/' + 'img_'+myms+'_data'
         pcal_prefix  = MAPS  + '/' + 'img_'+myms+'_pcal' 

         # job kill file for each of the datasets
         kill_file = SCRIPTS  + '/' + 'kill_jobs_'+ myms +'.sh'
         
         #-------------------------------------------------------------------------------
         # Make Copies of Data

         # name of slurm and the campanying log file to be executed
         bash_script = SCRIPTS  + '/' + myms+'_cp.sh' # name of the slurm file # loop
         logfile   = LOGS     + '/' + myms+'_cp.log'  # name of log file # loop


         # check existence of data in msback directory
         if path.exists(ms_path):
           # get the path to the file in the current directory
           src = path.realpath(ms_path) # store the file path in the variable 'src' if .txt file exists
         else:
           print("The data you're looking for is not stored in the directory: " + MS_BAK_DIR + '\n Please move data to ' + MS_BAK_DIR)
         
         # this part of the code isolate the file extension of the file being copied
         root, sep, extension = src.partition('.')
         
         # assigning myms an extension
         myms_ext = MS_DIR  + '/' + myms + '.' + extension

         # the name and path to copy the file to
         dst = MS_DIR  + '/' + myms + '.' + extension

         # checks if copy already exists in current dir
         if os.path.exists(dst):
           print("#------------------------------------\n")
           print("MS files already exists in the ms_files directory\n")
           print("#------------------------------------\n")
         else:
           
           # this variable constitutes the bash command that is gonna all the copying  
           bash_command = 'cp -r ' + src + ' ' + dst # + '.' + extension 

           # write the slurm file
           beta.write_slurm(opfile = bash_script,
                           jobname = 'cp_' + myms,
                           logfile = logfile,
                           syscall = bash_command) 
           
           # slurm job name
           job_id_copy = 'cp_' + myms 
           syscall     = job_id_copy + "=`sbatch "+bash_script+" | awk '{print $4}'`"
           f.write(syscall+'\n')

         #-------------------------------------------------------------------------------
         # Flag Summary, First

         bash_script = SCRIPTS  + '/' + myms+'_flag_sum1.sh' # name of the slurm file
         logfile   = LOGS     + '/' + myms+'_flag_sum1.log'  # name of log file

         syscall  = 'singularity exec '+CASA_CONTAINER+' '
         syscall += 'casa -c ' + cwd + '/gamma_flag_summary.py ' + myms_ext + ' --nologger --log2term --nogui\n'
         beta.write_slurm(opfile  = bash_script,
                         jobname = 'flag_sum1_' + myms,
                         logfile = logfile,
                         syscall = syscall)

         job_id_flag_sum1 = 'FLAG_SUM1_' + myms
         syscall = job_id_flag_sum1 + "=`sbatch -d afterok:${"+job_id_copy+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')

         #------------------------------------------------------------------------------
         # BDSF Island Mask Export

         if fitsmask == 'none':

             # split the isl and pix into their individual variables
             isl, pix = isl_pix.split(';')

             # fetch the mask from current directory
             img_name = glob.glob('masking_dummy.fits')[0]

             bash_script = SCRIPTS  + '/' + myms + '_mask.sh' # name of the slurm file
             logfile   = LOGS     + '/' + myms + '_mask.log'  # name of log file

             syscall = 'singularity exec '+SOURCE_FINDING_CONTAINER+' '
             syscall += 'python ' + cwd + '/delta_src_fnd.py ' + myms + ' ' + str(isl) + ' ' + str(pix) + ' ' + img_name + '\n'
             beta.write_slurm(opfile  = bash_script,
                             jobname = 'bdsf_' + myms,
                             logfile = logfile,
                             syscall = syscall)

             # set the newly created mask as the fitsmask
             fitsmask    = cwd + '/bdsf/' + myms + '_bdsf_mask.fits' 
             job_id_bdsf = 'BDSF_' +myms
             syscall     = job_id_bdsf + "=`sbatch -d afterok:${"+job_id_flag_sum1+"} "+bash_script+" | awk '{print $4}'`"
             f.write(syscall+'\n')


         #------------------------------------------------------------------------------
         # Automask wsclean

         # choose appropriate fitsmask for run
         if path.exists(fitsmask):
             fitsmask = fitsmask
         else:
             fitsmask = 'auto'        

         # This sets up the command for wsclean
         bash_script = SCRIPTS + '/' + myms+'_wsclean_data.sh' # name of the slurm file # there needs to be one of these for all the ms files
         logfile   = LOGS    + '/' + myms+'_wsclean_data.log'  # name of log file # loop over this
         syscall   = 'singularity exec '+WSCLEAN_CONTAINER+' ' # loop over this
         syscall  += beta.generate_syscall_wsclean(mslist = [myms_ext], # loop over this
                                                 imgname = blind_prefix,
                                                 datacol = 'DATA',
                                            minuvw_range = min_uvw,
                                                    bda  = False,
                                                    mask = fitsmask)


         # This is what actually generates the command in a bash file
         beta.write_slurm(opfile = bash_script,
                        jobname = 'data_' + myms,
                        logfile = logfile,
                        syscall = syscall)

         # To make sure that this job waits for the previous jobs accordingly,I'm lazily putting an if statement like I did above
         if path.exists(cwd + '/bdsf/' + myms + '_bdsf_mask.fits'):
             job_id_blind = 'DATA_' + myms 
             syscall = job_id_blind+"=`sbatch -d afterok:${"+job_id_bdsf+"} "+bash_script+" | awk '{print $4}'`"
             f.write(syscall+'\n')
         else:
             job_id_blind = 'DATA_' + myms
             syscall = job_id_blind+"=`sbatch -d afterok:${"+job_id_flag_sum1+"} "+bash_script+" | awk '{print $4}'`"
             f.write(syscall+'\n')

         # ------------------------------------------------------------------------------
         # Predict

         bash_script = SCRIPTS + '/' + myms+'_predict.sh' # name of the slurm file
         logfile   = LOGS + '/' + myms+'_predict.log'   # name of log file
         syscall   = 'singularity exec ' + WSCLEAN_CONTAINER + ' '  # for each of the msfiles
         syscall  += beta.generate_syscall_predict(msname = myms_ext,
                                                imgbase = blind_prefix)


         # This is what actually generates the command in a bash file
         beta.write_slurm(opfile = bash_script,
                        jobname = 'predict_' + myms,
                        logfile = logfile,
                        syscall = syscall)
 
         job_id_predict1 = 'PREDICT_' + myms
         syscall = job_id_predict1 + "=`sbatch -d afterok:${"+job_id_blind+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n') # loop

         # ------------------------------------------------------------------------------
         # Self-calibrate phases

         bash_script = SCRIPTS + '/' + myms + '_phase_cal.sh' # name of the slurm file
         logfile   = LOGS + '/' + myms + '_phase_cal.log'  # name of log file

         syscall   = 'singularity exec '+CASA_CONTAINER+' '
         syscall  += 'casa -c ' + cwd + '/epsilon_selfcal_target_phases.py ' + myms_ext + ' ' + uv_range + ' --nologger --log2term --nogui\n'
         beta.write_slurm(opfile  = bash_script,
                         jobname  = 'phase_cal_' + myms,
                         logfile  = logfile,
                         syscall  = syscall)

         job_id_phasecal1 = 'PHASECAL_' + myms
         syscall = job_id_phasecal1 + "=`sbatch -d afterok:${"+job_id_predict1+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')
         
         # ------------------------------------------------------------------------------
         # Flag Summary, Second

         bash_script = SCRIPTS + '/' + myms + '_flag_sum2.sh' # name of the slurm file
         logfile   = LOGS + '/' + myms + '_flag_sum2.log'  # name of log file

         syscall  = 'singularity exec '+CASA_CONTAINER+' '
         syscall += 'casa -c ' + cwd + '/gamma_flag_summary.py ' + myms_ext + ' --nologger --log2term --nogui\n'
         beta.write_slurm(opfile = bash_script,
                         jobname = 'flag_sum2_' + myms,
                         logfile = logfile,
                         syscall = syscall)

         job_id_flag_sum2 = 'FLAG_SUM2_' + myms
         syscall = job_id_flag_sum2 + "=`sbatch -d afterok:${"+job_id_phasecal1+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')

         # ------------------------------------------------------------------------------
         # WSCLEAN CORRECTED_DATA

         # choose appropriate fitsmask for run
         if path.exists(fitsmask):
             fitsmask = fitsmask
         else:
             fitsmask = 'auto'

         # This sets up the command for wsclean
         bash_script = SCRIPTS + '/' + myms+'_wsclean_correct.sh' # name of the slurm file
         logfile   = LOGS + '/' + myms+'_wsclean_correct.log'  # name of log file

         syscall  = 'singularity exec '+WSCLEAN_CONTAINER+' '
         syscall += beta.generate_syscall_wsclean(mslist      = [myms_ext],
                                                 imgname      = pcal_prefix,
                                                 datacol      = 'CORRECTED_DATA',
                                                 minuvw_range = min_uvw,
                                                 bda          = False,
                                                 mask         = fitsmask)

         # call function that writes the header info of a bash script
         beta.write_slurm(opfile  = bash_script,
                          jobname = 'wcorr_' + myms,
                          logfile = logfile,
                          syscall = syscall)


         job_id_PCAL1 = 'CORRECT_' + myms
         syscall = job_id_PCAL1 + "=`sbatch -d afterok:${"+job_id_flag_sum2+"} "+bash_script+" | awk '{print $4}'`"
         #syscall = job_id_PCAL1 + "=`sbatch "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')

         # ------------------------------------------------------------------------------
         # Image statistics, First

         bash_script = SCRIPTS + '/' + myms+'_img_stat.sh'
         logfile   = LOGS + '/' + myms+'_img_stat.log'  

         # write headings to image data file
         image_data = IMG_STATS + '/' + myms + '_img_stat.dat'
         beta.write_table(opfile = image_data)

         #
         syscall = 'singularity exec '+CASA_CONTAINER+' '
         syscall += 'casa -c ' + cwd + '/zeta_image_stats.py ' + pcal_prefix + '-MFS-image.fits' + ' ' + myms + ' --nologger --log2term --nogui\n'
         beta.write_slurm(opfile  = bash_script,
                          jobname = 'img_stat_' + myms,
                          logfile = logfile,
                          syscall = syscall)

         job_id_im_stat1 = 'IMG_STAT_' + myms
         syscall = job_id_im_stat1+"=`sbatch -d afterok:${"+job_id_PCAL1+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')

         #-------------------------------------------------------------------------------
         # Clean Up Empty Logging Files

         bash_script = SCRIPTS + '/' + myms+'_clean_up.sh' # name of the slurm file
         logfile   = LOGS + '/' + myms+'_clean_up.log'  # name of log file

         # this variable constitutes the bash command that is gonna all the copying  
         bash_command ='mv casa*.log ipython*.log *.last ./casa_junk/ && mv *.py ./IRIvBF && find ./ -empty -delete -print &>removed_logs.txt' 

         # write the slurm file
         beta.write_slurm(opfile = bash_script,
                         jobname = 'clean_up_' + myms,
                         logfile = logfile,
                         syscall = bash_command)

         job_id_rem_log = 'CLEAN_UP_' + myms
         syscall = job_id_rem_log+"=`sbatch -d afterok:${"+job_id_im_stat1+"} "+bash_script+" | awk '{print $4}'`"
         f.write(syscall+'\n')

         # ------------------------------------------------------------------------------
         # not using the kill file for now
         #kill = 'echo "scancel "$'+job_id_copy+'" "$'+job_id_flag_sum1+'" "$'+job_id_blind+'" "$'+job_id_predict1+'" "$'+job_id_phasecal1+'" "$'+job_id_flag_sum2+'" "$'+job_id_PCAL1+'" "$'+job_id_im_stat1+' >> 
         #'+kill_file
         #f.write(kill+'\n')

    f.close() # close function

if __name__ == "__main__":


    main()
