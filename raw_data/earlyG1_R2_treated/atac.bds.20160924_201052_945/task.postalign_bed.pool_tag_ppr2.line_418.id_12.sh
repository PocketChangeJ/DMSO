#!/bin/bash -e

cd '/srv/gsfs0/projects/kundaje/users/annashch/dmso/earlyG1_R2_treated'

# SYS command. line 420

 if [[ -f $(which conda) && $(conda env list | grep bds_atac | wc -l) != "0" ]]; then source activate bds_atac; fi;  export PATH=/home/annashch/bds_atac/.:/home/annashch/bds_atac/modules:/home/annashch/bds_atac/utils:${PATH}:/bin:/usr/bin:/usr/local/bin:${HOME}/.bds; set -o pipefail; STARTTIME=$(date +%s); renice -n 0 $$

# SYS command. line 422

 zcat /srv/gsfs0/projects/kundaje/users/annashch/dmso/earlyG1_R2_treated/out/align/pseudo_reps/rep1/pr2/H9_Fucci_earlyG1_R2_D1_S37_L005_R1_001.trim.PE2SE.nodup.pr2.tn5.tagAlign.gz /srv/gsfs0/projects/kundaje/users/annashch/dmso/earlyG1_R2_treated/out/align/pseudo_reps/rep2/pr2/H9_Fucci_earlyG1_R2_D2_S38_L005_R1_001.trim.PE2SE.nodup.pr2.tn5.tagAlign.gz  | gzip -c > /srv/gsfs0/projects/kundaje/users/annashch/dmso/earlyG1_R2_treated/out/align/pooled_pseudo_reps/ppr2/H9_Fucci_earlyG1_R2_D1_S37_L005_R1_001.trim.PE2SE.nodup.pr2.tn5_pooled.tagAlign.gz

# SYS command. line 424

 TASKTIME=$[$(date +%s)-${STARTTIME}]; if [ ${TASKTIME} -lt 60 ]; then echo "Waiting for $[60-${TASKTIME}] seconds."; sleep $[60-${TASKTIME}]; fi