#This script implements the method in http://science.sciencemag.org/content/early/2016/10/05/science.aag2445
#see methods page 13 - 17
import pdb 
import argparse
import numpy as np
import cPickle as pickle
import math

def parse_args():
    parser=argparse.ArgumentParser(description="Maps peak to genes using method in Lander, Engreitz, et al.")
    parser.add_argument("--gene_list")
    parser.add_argument("--promoter_to_gene")
    parser.add_argument("--h3k27ac_bdg_file")
    parser.add_argument("--atac_limma_file")
    parser.add_argument("--atac_limma_column",type=int)
    parser.add_argument("--atac_rpm_file")
    parser.add_argument("--atac_rpm_column",type=int) 
    parser.add_argument("--nij_hic_base_dir")
    parser.add_argument("--hic_resolution",type=int,default=40000)
    parser.add_argument("--hic_suffix",default=".sparse_map")
    parser.add_argument("--outf")
    parser.add_argument("--runall",action="store_true")
    return parser.parse_args() 

#NOTE: THIS ASSUMES THE HUMAN GENOME, CHANGE THE CHROMOSOME RANGE FOR NON-HUMAN GENOME!!
def make_contact_map(nij_base_dir,hic_resolution,suffix):
    contact_map=dict()
    for chrom in range(1,24):
        chrom_contacts=open(nij_base_dir+"/"+"nij.chr"+str(chrom)+suffix,'r').read().strip().split('\n')
        print("read in chrom contacts:"+str(chrom))
        contact_map['chr'+str(chrom)]=dict()
        c=0 
        for line in chrom_contacts:
            c+=1 
            if (c % 10000 ==0):
                print str(c) 
            tokens=line.split('\t')
            bin1=int(tokens[0])#*hic_resolution
            bin2=int(tokens[1])#*hic_resolution
            frequency=float(tokens[2])
            if bin1 not in contact_map['chr'+str(chrom)]:
               contact_map['chr'+str(chrom)][bin1]=dict()
            contact_map['chr'+str(chrom)][bin1][bin2]=frequency
        print("built contact map for chromosome:"+str(chrom))
    return contact_map 

def get_hic_bin_to_gene(promoter_to_gene_file,gene_list,hic_resolution):
    gene_dict=dict()
    for gene in gene_list:
        gene_dict[gene]=1 
    data=open(promoter_to_gene_file,'r').read().strip().split('\n')
    hic_bin_to_gene=dict()
    for line in data:
        tokens=line.split('\t')
        chrom=tokens[0]
        pos=int(tokens[1])
        gene_name=tokens[4]
        if gene_name in gene_dict:
            #get the hic bin
            hic_bin=pos/hic_resolution
            if chrom not in hic_bin_to_gene:
                hic_bin_to_gene[chrom]=dict()
            if hic_bin not in hic_bin_to_gene[chrom]:
                hic_bin_to_gene[chrom][hic_bin]=[gene_name]
            else:
                hic_bin_to_gene[chrom][hic_bin].append(gene_name)
    return hic_bin_to_gene

def get_hic_bin_to_peak(atac_limma_file,atac_limma_column,hic_resolution):
    hic_bin_to_peak=dict()
    peak_file=open(atac_limma_file,'r').read().strip().split('\n')
    for line in peak_file[1::]: #first line is header that should be skipped
        tokens=line.split('\t')
        chrom=tokens[0]
        start=int(tokens[1])
        end=int(tokens[2])
        peak=chrom+"_"+str(start)+"_"+str(end)
        fc=float(tokens[atac_limma_column])
        if abs(fc)>=1:
            bin1=start/hic_resolution
            bin2=end/hic_resolution
            if chrom not in hic_bin_to_peak:
                hic_bin_to_peak[chrom]=dict()
            if bin1 not in hic_bin_to_peak[chrom]:
                hic_bin_to_peak[chrom][bin1]=[peak]
            else:
                hic_bin_to_peak[chrom][bin1].append(peak)
            if bin2!=bin1: #store the peak again in bin2
                if bin2 not in hic_bin_to_peak[chrom]:
                    hic_bin_to_peak[chrom][bin2]=[peak]
                else:
                    hic_bin_to_peak[chrom][bin2].append(peak)
    return hic_bin_to_peak

def get_atac_rpm(atac_rpm_file,atac_rpm_column):
    data=open(atac_rpm_file,'r').read().strip().split('\n')
    atac_rpm=dict()
    for line in data[1::]: #skip header line
        tokens=line.split('\t')
        peak='_'.join(tokens[0:3])
        value=float(tokens[atac_rpm_column])
        atac_rpm[peak]=value 
    return atac_rpm

    
def get_h3k27ac_rpm(h3k27ac_rpm_file):
    data=open(h3k27ac_rpm_file,'r').read().strip().split('\n')
    h3k27ac_rpm=dict()
    for line in data:
        tokens=line.split('\t')
        peak='_'.join(tokens[0:3])
        value=float(tokens[3])
        h3k27ac_rpm[peak]=value 
    return h3k27ac_rpm

def intersect_h3k27ac_atac(atac_rpm,h3k27ac_rpm):
    combined_rpm=dict() 
    #hash k27ac to nearest 1 kb
    h3k27ac_1kb_hash=dict()
    for peak in h3k27ac_rpm:
        peak_parts=peak.split('_')
        chrom=peak_parts[0]
        start_pos=int(peak_parts[1])/1000
        hash_key=tuple([chrom,start_pos])
        if hash_key not in h3k27ac_1kb_hash:
            h3k27ac_1kb_hash[hash_key]=[tuple([peak,h3k27ac_rpm[peak]])]
        else:
            h3k27ac_1kb_hash[hash_key].append(tuple([peak,h3k27ac_rpm[peak]]))
    print("generated 1kb hash of h3k27ac data")
    for peak in atac_rpm:
        peak_parts=peak.split('_')
        chrom=peak_parts[0]
        start_pos=int(peak_parts[1])/1000
        hash_key=tuple([chrom,start_pos])
        if hash_key in h3k27ac_1kb_hash:
            closest_peak_dist=None
            closest_peak_mag=None 
            #keep this peak, get the h3k27ac signal for the nearest overlapping peak within this hash bin.
            for h3k27ac_peak in h3k27ac_1kb_hash[hash_key]:
                #store the index of the closest peak!
                dist=int(h3k27ac_peak[0].split('_')[1])
                if (closest_peak_dist==None) or (dist < closest_peak_dist):
                    closest_peak_mag=h3k27ac_peak[1]
            combined_rpm[peak]=[atac_rpm[peak],closest_peak_mag]
    return combined_rpm #peak --> [atac peak rpm, h3k27ac overlapping peak rpm]# 

def get_predicted_impact(contact_map,hic_bin_to_gene,hic_bin_to_peak,peak_intersection):
    impact_scores=dict()
    #do one chromosome at a time
    #pdb.set_trace()
    hits=0
    for chrom in hic_bin_to_gene:
        if chrom not in contact_map:
            print("WARNING: chromosomes:"+chrom+" is not in the contact map dictionary, skipping!")
            continue 
        for b1 in hic_bin_to_gene[chrom]:
            if b1 not in contact_map[chrom]:
                continue
            for gene in hic_bin_to_gene[chrom][b1]:
                for b2 in hic_bin_to_peak[chrom]:
                    if b2 not in contact_map[chrom][b1]:
                        continue
                    for peak in hic_bin_to_peak[chrom][b2]: 
                    #record the entry if there is a contact across the two bins
                        if peak not in peak_intersection:
                            continue #we skip the atac peaks that don't have a corresponding h3k27ac peak. 
                        contact_freq=contact_map[chrom][b1][b2]
                        atac_peak_rpm=peak_intersection[peak][0]
                        h3k27ac_peak_rpm=peak_intersection[peak][1]
                        try:
                            predicted_impact=math.log(atac_peak_rpm*
                                                      h3k27ac_peak_rpm*
                                                      contact_freq*
                                                      contact_freq,
                                                      2)
                            impact_scores[tuple([gene,peak])]=predicted_impact
                            print(str(gene)+'\t'+str(peak)+'\t'+str(predicted_impact)) 
                        except:
                            continue
    return impact_scores

def main():
    args=parse_args()
    if args.runall==True: 
        genes=open(args.gene_list,'r').read().strip().split('\n')
        #things associated with hi-c contact distance

        contact_map=make_contact_map(args.nij_hic_base_dir,args.hic_resolution,args.hic_suffix)
        print("loaded contact map!")
        pickle.dump(contact_map,open("contact_map.npy",'wb'),protocol=2)
        print("save contact map!")

        hic_bin_to_gene=get_hic_bin_to_gene(args.promoter_to_gene,genes,args.hic_resolution)
        print("got hic bins for genes")
        pickle.dump(hic_bin_to_gene,open("hic_bin_to_gene.npy",'wb'),protocol=2)
        print("saved hic_bin_to_gene")

        hic_bin_to_peak=get_hic_bin_to_peak(args.atac_limma_file,args.atac_limma_column,args.hic_resolution) 
        print("got hic bins for peaks")
        pickle.dump(hic_bin_to_peak,open("hic_bin_to_peak.npy",'wb'),protocol=2)
        print("saved hic_bin_to_peak")

        #get the atac rpm    
        atac_rpm=get_atac_rpm(args.atac_rpm_file,args.atac_rpm_column)
        print("got atac-seq rpm")
        pickle.dump(atac_rpm,open("atac_rpm.npy",'wb'),protocol=2)
        print("saved atac_rpm") 

        #get the h3k27ac rpm
        h3k27ac_rpm=get_h3k27ac_rpm(args.h3k27ac_bdg_file)
        print("got h3k27ac rpm")
        pickle.dump(h3k27ac_rpm,open("h3k27ac_rpm.npy",'wb'),protocol=2)
        print("saved h3k27ac_rpm")

        #intersect the h3k27ac & atac peaks, bin to 1kb,
        #store the atac-seq original coordinates  & corresponding ATAC & h3k27ac value 
        peak_intersection=intersect_h3k27ac_atac(atac_rpm,h3k27ac_rpm)
        print("got peak intersection")
        pickle.dump(peak_intersection,open("peak_intersection.npy",'wb'),protocol=2)    
        print("saved peak_intersection")

    else: 
        contact_map=pickle.load(open("contact_map.npy","rb"))
        hic_bin_to_gene=pickle.load(open("hic_bin_to_gene.npy","rb"))
        hic_bin_to_peak=pickle.load(open("hic_bin_to_peak.npy","rb"))
        atac_rpm=pickle.load(open("atac_rpm.npy","rb"))
        h3k27ac_rpm=pickle.load(open("h3k27ac_rpm.npy","rb"))
        peak_intersection=pickle.load(open("peak_intersection.npy","rb"))
        print("loaded all numpy pickles with intermediate metrics")

    
    #use the intersected peaks to find contact maps !
    impact_scores=get_predicted_impact(contact_map,hic_bin_to_gene,hic_bin_to_peak,peak_intersection)

    #save the impact scores to an output file
    outf=open(args.outf,'w')
    outf.write('Gene\tPeak\tScore\n')
    for entry in impact_scores:
        outf.write(entry[0]+'\t'+entry[1]+'\t'+str(impact_scores[entry])+'\n')
        
if __name__=="__main__":
    main()
