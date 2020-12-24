import matplotlib
from matplotlib.pyplot import *
import matplotlib.pyplot as plt
from astropy.io import fits
from astropy.table import Table
from scipy.optimize import curve_fit
import numpy as np
import scipy as sc
from scipy import stats
from scipy.stats import norm
from astropy  import units as u
from astropy import constants as const
import scipy as sp
from scipy.integrate import quad
from scipy import integrate
import math
from scipy.signal import convolve
from scipy import interpolate
from scipy.interpolate import interp1d
import time
from astropy.cosmology import FlatLambdaCDM
from astropy import units as u
from scipy.stats import norm
import matplotlib.mlab as mlab
import sys
from astropy.table import hstack
from astropy.table import vstack
from functions import *



timer_start=time.time()

from config import *
#----------------------------------------
#Loading Data

#--------------------------------------------------------------------------
#Functions


def S(i,j,k):
    sed=((1.-g[k])*dat1[:,i,j]+g[k]*dat2[:,i,j])
    ss=interp1d(dat3, sed, bounds_error=False,fill_value=0, kind='linear')
    sed=ss(RFull)
    #sed=sed*Lsol*(np.sqrt(integrate.trapz(sed,RFullnu)**2))**-1  #Normaliser
    sed=np.array(sed)
    return sed

#------------------------------------------------------------------------------
'''
#Load filters
filter_arr=Table.read('filters/ft.fits')
filter_l=filter_arr['lambda']

filt=[]
for col in filter_arr[filtname].colnames:
    filt.append(np.array(filter_arr[col]))

print(len(filt))
'''

assert len(sfx)==len(FILTERS)==len(band_names)==len(err_band_names),'ERROR: Filter range does not match available photometry, check band names'


print('Photometry range ok')

#---------------------------------------------------------
#Pull GB optical and AGN templates
from template_importer import *

#---------------------------------------------------------
#Convolution with filters is done here
#First choose the galaxy from gal list and define z


def galproc(galaxy):
    galaxy_index=galaxy
    if verbose:
        print ('Calculating index:',(P[galaxy_index,0]))


    z=P[galaxy_index,1]

    try:
        Mstar=P[galaxy_index,2]
    except:
        Mstar=-99

    if extra_bands:
        sfx_extra=W_ex[galaxy_index,:]

    #Redshift the template range
    RFullred=RFull*(1+z)
    start = time.time()


    #=======================================
    #



    flux_i=G[galaxy_index,:]*10**-3
    flux_i_e=E[galaxy_index,:]*10**-3
    flux_i_e_orig=np.copy(flux_i_e)

    snr=flux_i/flux_i_e
    wav_ar_i=W[galaxy_index,:]

    try:
        lastdet=(wav_ar_i[snr>3][-1])/(1+z)
    except:
        lastdet=-99



    mask=[]
    for i,obj in enumerate(flux_i):
        snr=flux_i[i]/flux_i_e[i]
        if snr<=3. and flux_i[i]>10**-11 and flux_i_e[i]>10**-10:
            flux_i_e[i]=3.*flux_i_e[i] #Upper limit
        elif flux_i[i]<10**-11:
            mask.append(i)
        else:
            continue


    flux=np.delete(flux_i, mask,None)
    flux_e=np.delete(flux_i_e, mask,None)
    flux_e_orig=np.delete(flux_i_e_orig,mask,None)
    wav_ar=np.delete(wav_ar_i,mask,None)

    #Create extra filters and add them to the existing filter array
    if extra_bands:
        filt_extra=np.array(filter_cont(sfx_extra,5,0.2))
        if verbose==2:
            print(f'Created square waves at {sfx_extra} um')

    #SNR reducer


    for i,obj in enumerate(wav_ar):
        if wav_ar[i]<=25.:
            if flux[i]/flux_e[i]>=5:
                flux_e[i]=flux[i]*(1./5.) # REDUCE THE IMPORTANCE OF STELLAR DATA


    lum_dist=(cosmo.luminosity_distance(z)).to(u.cm).value

    try:
        FL=(1.+z)*(4.*pi*lum_dist**2)**-1
    except:
        print('Failed at ID ', P[galaxy_index,0])
        return None



    #==========================================================================
    #SYNTHETIC PHOTOMETRY
    timer_synphot=time.time()

    '''Create empty arrays to fill in'''

    #DL07
    DL07=np.zeros((len(sfx),len(dat1[0,:,0]),len(dat1[0,0,:]),len(g)))
    agn_c=np.zeros((len(sfx),len(agn[:,0])))
    GB_T=np.zeros((len(sfx),len(GB[:,0])))

    if extra_bands:
        DL07_ex=np.zeros((len(sfx_extra),len(dat1[0,:,0]),len(dat1[0,0,:]),len(g)))
        agn_c_ex=np.zeros((len(sfx_extra),len(agn[:,0])))
        GB_T_ex=np.zeros((len(sfx_extra),len(GB[:,0])))


    for i,obj in enumerate(dat1[0,:,0]):
        for j,obj in enumerate(dat1[0,0,:]):
            for k,obj in enumerate(g):
                SED=S(i,j,k)*FL
                for p,obj in enumerate(sfx):
                    DL07[p,i,j,k]=convolver(RFullred,SED,FILTERS[p][0],FILTERS[p][1],sfx[p])




                if extra_bands:
                    for p,obj in enumerate(sfx_extra):
                        DL07_ex[p,i,j,k]=convolver(RFullred,SED,filt_extra[p][0],filt_extra[p][1],sfx_extra[p])

    #AGN

    for i,obj in enumerate(agn[:,0]):
        for p,obj in enumerate(sfx):
            agn_c[p,i]=convolver(RFullred,agn[i,:],FILTERS[p][0],FILTERS[p][1],sfx[p])

        if extra_bands:
            for p,obj in enumerate(sfx_extra):
                agn_c_ex[p,i]=convolver(RFullred,agn[i,:],filt_extra[p][0],filt_extra[p][1],sfx_extra[p])
    #GB

    GB_T=np.zeros((len(sfx),len(GB[:,0])))
    for i,obj in enumerate(GB[:,0]):
        for p,obj in enumerate(sfx):
            GB_T[p,i]=convolver(RFullred,GB[i,:],FILTERS[p][0],FILTERS[p][1],sfx[p])

        if extra_bands:
            for p,obj in enumerate(sfx_extra):
                GB_T_ex[p,i]=convolver(RFullred,GB[i,:],filt_extra[p][0],filt_extra[p][1],sfx_extra[p])



    if extra_bands:
        DL07=np.concatenate([DL07,DL07_ex],axis=0)
        agn_c=np.concatenate([agn_c,agn_c_ex],axis=0)
        GB_T=np.concatenate([GB_T,GB_T_ex],axis=0)

    time_synphot=time.time()-timer_synphot

    if verbose>1:
        print('Synthetic Photometry - ',time_synphot,'s')


    #==========================================================================

    '''
    (Re)Normalising Templates to perform the fit
    '''
    b=10**10*(const.M_sun/const.m_p)*dust_switch
    b1=1/np.mean(GB)*stellar_switch
    b2=1/np.mean(agn)*agn_switch


    #-------------------------------------
    #Masking template entries with no photometry
    DL07=np.delete(DL07, mask,axis=0)
    GB_T=np.delete(GB_T,mask,axis=0)
    agn_c=np.delete(agn_c,mask,axis=0)



    sort=np.argsort(wav_ar)
    flux=flux[sort]
    flux_e=flux_e[sort]
    wav_ar=wav_ar[sort]
    DL07=DL07[sort]
    GB_T=GB_T[sort]
    agn_c=agn_c[sort]


    #-------------------------------------
    A=[]
    CHI=np.zeros_like(DL07[0,:,:,:])
    SOL=np.zeros((15,len(DL07[0,:,0,0]),len(DL07[0,0,:,0]),len(DL07[0,0,0,:])))

    for i,obj in enumerate(GB_T[0,:]):
        A.append(b1*GB_T[:,i])


    A.append(b2*agn_c[:,0])
    A.append(b2*agn_c[:,1])
    '''Can insert DL linear combination here'''
    A.append(0*agn_c[:,1]) #Adding a fake row as a placeholder for DL07



    fit_start=time.time()
    for i1,obj in enumerate(dat1[0,:,0]):
        for i2,obj in enumerate(dat1[0,0,:]):
            for i3,obj in enumerate(g):
                B=np.copy(A)
                B[-1,:]=b*DL07[:,i1,i2,i3]
                B=np.array(B)
                B=B/flux_e
                B=B.T
                try:
                    nnsol, ier = sp.optimize.nnls(B,flux/flux_e)
                    SOL[:,i1,i2,i3]=nnsol
                    CHI[i1,i2,i3]=ier**2


                except:
                    nnsol = np.array([0.]*total)
                    ier=-99


    for i1,obj in enumerate(dat1[0,:,0]):
        for i2,obj in enumerate(dat1[0,0,:]):
            for i3,obj in enumerate(g):
                if CHI[i1,i2,i3]==np.amin(CHI):
                    minsol=np.array([i1,i2,i3])



    nnsol=SOL[:,minsol[0],minsol[1],minsol[2]]
    chi2=CHI[minsol[0],minsol[1],minsol[2]]



    A[-1]=b*DL07[:,minsol[0],minsol[1],minsol[2]]
    A=np.array(A)
    bestfit=np.copy(A)
    A=A/flux_e
    A=A.T


    lll=len(dat1[0,:,0])*len(dat1[0,0,:])*len(g)
    SOL_f=SOL.reshape(15,int(lll))
    CHI_f=CHI.flatten()
    deltaCHI=(CHI_f/(len(flux)-1))-(chi2/(len(flux)-1))
    #CHImask=np.argsort(CHI_f)
    #CHImask=CHImask[0:np.int(0.3*len(CHImask))]
    CHImask=deltaCHI<1.3
    SOL_13=SOL_f[:,CHImask]

    covmask=np.argwhere(nnsol==0)
    covmask2=nnsol>0
    nnsol_mask=np.delete(nnsol,covmask,None)
    C=np.delete(A,covmask,axis=1)


    vec=chi_vectors(A,SOL_13)



    'Producing the covariance matrix from template matrix A, and solution nnsol'
    try:
        cov = np.matrix(np.dot(C.T, C)).I.A
        covsam=np.random.multivariate_normal(nnsol_mask,cov,10**3)
        incl_val=[]
        for val in range(len(covsam[:,0])):
            if all(h>0 for h in covsam[val,:]):
                incl_val.append(val)
        covsam=covsam[incl_val,:]
        nnsol_cov=np.zeros((len(covsam[:,0]),len(nnsol)))
        nnsol_cov[:,covmask2]=covsam
    except:
        nnsol_cov=nnsol


    #------------------------------------------------------------------
    #Functions

    def f_opt(x,*params): #Fitted photometry
        l=np.arange(0,len(x),1)
        #q=qpah
        #g=g_index
        #q2=qpah2
        params=np.array(params)
        r=np.sum(params*bestfit,axis=1)
        return r

    def stellar(*params): #Stellar template
        params=np.array(params)
        optt=params*np.array(GB.T)
        optt=np.sum(optt,axis=1)
        return b1*optt


    def agnpl(*params):  #AGN template
        params=np.array(params)
        a=params*b2*agn.T
        a=np.sum(a,axis=1)
        return a


    def full_ir(*params): #IR template
        params=np.array(params)
        r=[]
        r.append(S(minsol[0],minsol[1],minsol[2]))
        r=np.array(r)
        r=params*r.T
        return b*FL*(np.sum(r,axis=1))


    def full_template(*params): #All combined
        params=np.array(params)
        s=stellar(params[:steltemp])
        i=full_ir(params[total-irtemp:])
        a=agnpl(params[steltemp:steltemp+agntemp])
        return s+a+i

    '''
    This computes LIR, given the template function and the solution vector
    '''
    def LumIR(f,param):
        flux=f(*param)*10**-26
        luminosity_v=((4*pi*lum_dist**2*flux*(1+z)**-1)*u.erg).si
        wavrange=[find_nearest(RFull,8),find_nearest(RFull,1000)+1]
        luminosity_v=luminosity_v[wavrange[0]:wavrange[1]]
        wavelength=((RFull[wavrange[0]:wavrange[1]]*(1.+0))*u.um).si
        Luminosity_IR=integrate.trapz((luminosity_v*c*wavelength**-2).value,wavelength.value)*(3.839*10**26)**-1

        return Luminosity_IR

    #---------------------------------------------------
    chi2red_nnls=chi2/(len(flux)-1)
    #---------------------------------------------------
    #Finding initial values for quantities of interest

    Lir_draine=LumIR(full_ir,nnsol[(total-irtemp):])
    Lir_total=LumIR(full_template,nnsol)
    Lir_stellar=LumIR(stellar,nnsol[:steltemp])



    Lagn=(Lir_total-Lir_draine)
    fagn=(Lir_total-Lir_draine)/Lir_total

    if np.isfinite(fagn):
        fagn=fagn
    else:
        fagn=0.
    SFR=Lir_draine*10**-10


    Mgas_nnls=nnsol[-1]*b*(const.m_p/const.M_sun)

    Mdust=DG_ratio*Mgas_nnls



    U=Lir_total/(125*Mdust)

    reddest_flux=DL07[-1,:,:,:].flatten()
    reddest_flux/=np.median(reddest_flux)
    reddest_flux=reddest_flux[deltaCHI<1.3]



    print(np.std(np.log10(reddest_flux)))
    #sys.exit()
    x = np.arange(-2, 2, .1)
    scatt = stats.norm.pdf(x,scale=0.3)
    scatt /= np.sum(scatt)
    dex_sigma=np.std(np.log10(reddest_flux))


    #Metallicity from Manucci+10 eq5
    #------------------------------------------------------
    if Mstar==-99:
        Mgas=deltaGDR=-99
    else:
        Mgas,deltaGDR=mgas_metallicity_manucci(Mstar,Mdust,SFR)
    #------------------------------------------------------



    Mdust_cov=[]
    Lir_total_cov=[]
    Lir_draine_cov=[]
    eLir_total=eLir_draine=eLagn=eMD=eMG=efagn=-99
    max_allowed = 2
    attempt = 0
    loop_time_start=time.time()
    while (eLir_total<1.) or np.isnan(eLir_total) or (eMD<1.) or np.isnan(eMD):
        attempt+=1
        if attempt>max_allowed or time.time()-loop_time_start>1200:
            print('multivar_gauss: max attempts exceeded: TIMEOUT ERROR')
            break
        try:
            cov = np.matrix(np.dot(C.T, C)).I.A
            covsam=np.random.multivariate_normal(nnsol_mask,cov,attempt*10**3)
            incl_val=[]
            for val,_ in enumerate(covsam[:,0]):
                if all(h>0 for h in covsam[val,:]):
                    incl_val.append(val)
            covsam=covsam[incl_val,:]
            nnsol_cov=np.zeros((len(covsam[:,0]),len(nnsol)))
            nnsol_cov[:,covmask2]=covsam
        except:
            break


        try:
            nnsol_cov_sum=np.sum(nnsol_cov[:,total-irtemp:],axis=1)
            Mdust_cov=DG_ratio*nnsol_cov_sum*b*(const.m_p/const.M_sun)
            for x,obj in enumerate(nnsol_cov[:,0]):
                Lir_total_cov.append(LumIR(full_template,nnsol_cov[x,:]))
                Lir_draine_cov.append(LumIR(full_ir,nnsol_cov[x,(total-irtemp):]))

            Lagn_cov=np.array(Lir_total_cov)-np.array(Lir_draine_cov)
            fagn_cov=np.array(Lagn_cov)/np.array(Lir_total_cov)

            eLagn=mean_confidence_interval_fast_error(Lagn_cov,Lagn)
            eLir_draine=mean_confidence_interval_fast_error(Lir_draine_cov,Lir_draine)
            eLir_total=mean_confidence_interval_fast_error(Lir_total_cov,Lir_total)
            eMD=mean_confidence_interval_fast_error(Mdust_cov,Mdust)
            efagn=mean_confidence_interval_fast_error(fagn_cov,fagn)
            eMG=eMD*deltaGDR

        except:
            print('multivar_gauss: fail')
            break

    #----------------------------------------------------------------------------

    try:
        Lir_chi=[]
        Lir_draine_chi=[]
        Mdust_chi=[]
        for x,obj in enumerate(SOL_13[0,:]):
            Lir_chi.append(LumIR(full_template,SOL_13[:,x]))
            Lir_draine_chi.append(LumIR(full_ir,SOL_13[(total-irtemp):,x]))
            Mdust_chi.append(DGratio*SOL_13[-1,x]*b*(const.m_p/const.M_sun))

        Lir_chi=np.array(Lir_chi)
        Mdust_chi=np.array(Mdust_chi)
        Lir_total_cov=np.array(Lir_total_cov)
        Mdust_cov=np.array(Mdust_cov)
        CIL=mean_confidence_interval_fast(np.log10(Lir_chi))
        CIM=mean_confidence_interval_fast(np.log10(Mdust_chi))


        Lir_med=10**CIL[0]
        Mdust_med=10**CIM[0]

        Lir_med_err=np.mean([10**CIL[0]-10**CIL[1],10**CIL[2]-10**CIL[0]])
        Mdust_med_err=np.mean([10**CIM[0]-10**CIM[1],10**CIM[2]-10**CIM[0]])
    except:
        Lir_med=-99
        Mdust_med=-99
        Lir_med_err=-99
        Mdust_med_err=-99


    sU=(1/125)*np.sqrt((eLir_draine/Mdust)**2+(Lir_draine*eMD/Mdust**2)**2)


    CHI_13=CHI_f[CHImask]

    eMD=(eMD**2+(10**dex_sigma)**2)**0.5

    #cov_data=np.array([CHI_13,Lir_chi,Lir_draine_chi,Mdust_chi])
    #cov_names=['chi2','Lir_total','Lir_draine','MD',]
    #covar=Table(cov_data.T,names=cov_names,dtype=len(cov_names)*[float])
    #covar.write(covarloc+str(int(P[galaxy_index,0])) + '_covar_all_chi.fits',overwrite=True)
    '''
    def get_pdf(pdf,arr,range,bins=50):
        bins=np.linspace(range[0],range[1],bins)
        dig=np.digitize(arr,bins,right=True)
        pdf_sum=[]
        for i,_ in enumerate(bins):
            if len(pdf[dig==i])==0:
                weight=1
            else:
                weight=len(pdf[dig==i])
                #kweight=1
            pdf_sum.append(np.sum(pdf[dig==i])/weight)
        return np.array([bins,pdf_sum])

    pdf=np.exp(-CHI_13/2)

    fig= plt.figure(figsize=(10,10))

    ax = fig.add_subplot(2,2,1)
    med=np.log10(Lir_total)
    lir_total_pdf=get_pdf(pdf,np.log10(Lir_chi),range=[med-0.1,med+0.1])
    fill_between(lir_total_pdf[0],0,lir_total_pdf[1],alpha=0.5)
    ax.set_xlim(np.log10(Lir_total)-0.1,np.log10(Lir_total)+0.1)
    ax.set_ylim(0,)
    ax.set_yticklabels([])
    ax.set_ylabel('Probability')
    ax.set_xlabel(r'L$_{\rm IR,total}$')
    axvline(med)

    ax = fig.add_subplot(2,2,2)
    med=np.log10(Mdust)
    total_pdf=get_pdf(pdf,np.log10(Mdust_chi),range=[med-0.1,med+0.1])
    fill_between(total_pdf[0],0,total_pdf[1],alpha=0.5)
    ax.set_ylim(0,)
    ax.set_yticklabels([])
    ax.set_xlabel(r'M$_{\rm dust}$')
    axvline(med)
    '''
    if verbose:
        print('------------------------------------------')
        print ('ID:',int(P[galaxy_index,0]))
        print ('LIR:',"%.4g" % (Lir_total),'+-',"%.4g" % (eLir_total),'Lsol')
        print ('Mdust:',"%.4g" % Mdust ,'+-',"%.4g" % eMD,'Msol' )
        print ('chi2red:',"%.4g" % chi2red_nnls)
        print('------------------------------------------')

    #--------------------------------------------------
    if save_sed:

        def rad_flux(lam):
            alpha=-0.7
            return radio_slope(z,Lir_total,lum_dist)*lam**(-alpha)

        if radio:
            RADIO=rad_flux(RFull*(1.+z))
        else:
            RADIO=np.zeros_like(RFull)

        toSED=np.array([RFull*(1.+z),stellar(*nnsol[:(steltemp)]),agnpl(nnsol[steltemp:steltemp+agntemp]),full_ir(*nnsol[(total-irtemp):]),full_template(*nnsol),RADIO])
        tableSED=Table(toSED.T,names=['lambda','stellar','AGN','IR','Total','Radio'],dtype=[float,float,float,float,float,float])
        tableSED.write(sedloc+str(int(P[galaxy_index,0])) + ".fits",overwrite=True)

    #--------------------------------------------------

    if not multithread:
        fig= plt.figure(figsize=(10,5))
        ax = fig.add_subplot(1,1,1)
        textypos=0.9
        textxpos=0.6
        textsep=0.08

        if radio:
            radio_points=10**-3*np.array([DATA['FIR_10CM_FLUX'][galaxy_index],DATA['FIR_20CM_FLUX'][galaxy_index]])
            e_radio_points=10**-3*np.array([DATA['FIR_10CM_FLUXERR'][galaxy_index],DATA['FIR_20CM_FLUXERR'][galaxy_index]])
            radio_bands=np.array([10**5,2*10**5])
        #    radio_points=np.array([DATA['f3g'][galaxy_index],DATA['f14g'][galaxy_index]])
        #    e_radio_points=np.array([DATA['ef3g'][galaxy_index],DATA['ef14g'][galaxy_index]])

        #radio_points[1]=0.056852432
        #e_radio_points[1]=0.029326304000
        def rad_flux(lam):
            alpha=-0.7
            return radio_slope(z,Lir_total,lum_dist)*lam**(-alpha)

        #print('F10cm',rad_flux(10**5),'mJy')
        #print('F20cm',rad_flux(2*10**5),'mJy')
        #for i,_ in enumerate(nnsol_cov[:,0]):
        #    plt.plot(RFull*(1.+z),full_template(*nnsol_cov[i,:]),'gray',lw=3,alpha=0.1,zorder=-1)
        #plt.plot(RFull*(1.+z),full_template(*nnsol),'k',label='Total',lw=3,alpha=0.8)
        SF=stellar(*nnsol[:(steltemp)])
        AGN=agnpl(nnsol[steltemp:steltemp+agntemp])
        IR=full_ir(*nnsol[(total-irtemp):])

        if radio:
            RADIO=rad_flux(RFull*(1.+z))
            TOTAL=SF+AGN+IR+RADIO
        else:
            TOTAL=SF+AGN+IR

        #radio_bands=np.array([0.1,0.2])*10**6
        #radio_points=np.array([0.00055153, 0.0146874])
        #e_radio_points=np.array([0.00277811, 0.00711859])
        plt.fill_between(RFull*(1.+z),0,SF,color='royalblue',alpha=0.2,label='Stellar')
        plt.fill_between(RFull*(1.+z),0,AGN,color='g',alpha=0.2,label='AGN')
        plt.fill_between(RFull*(1.+z),0,IR,color='maroon',alpha=0.2,label='Dust')

        plt.plot(RFull*(1.+z),TOTAL,'k',label='Total',lw=3,alpha=0.6,zorder=10)


        #plt.plot(wav_ar,np.sum(nnsol*bestfit.T,axis=1),'bo')

        points=((flux/flux_e_orig)>=3)

        plt.errorbar(wav_ar[points],flux[points],yerr=flux_e_orig[points],color='red',fmt='s',capsize=5,capthick=1,ms=12,markerfacecolor='white',mew=2,barsabove=True)
        plt.scatter(wav_ar[~points],(flux+3*flux_e_orig)[~points],marker=r'$\downarrow$',s=300,color='red',zorder=11)
        if radio:
            points_radio=((radio_points/e_radio_points)>=3)
            plt.errorbar(radio_bands[points_radio],radio_points[points_radio],yerr=e_radio_points[points_radio],color='blue',fmt='o',capsize=5,capthick=1,ms=12,markerfacecolor='white',mew=2,barsabove=True)
            plt.scatter(radio_bands[~points_radio],(radio_points+3*e_radio_points)[~points_radio],marker=r'$\downarrow$',s=300,color='b',zorder=11)

        #add_text_to_ax(0.05, 0.95, r'ID {}'.format(int(P[galaxy_index,0])),ax=ax,fontsize=20, color='k')
        #add_text_to_ax(0.05, 0.95-textsep, r'z={:.2f}'.format(z),ax=ax,fontsize=20, color='k',usetex=True)

        plt.text(0.02, 0.85,'ID '+str(int(P[galaxy_index,0])), color='k',fontsize=20,transform=ax.transAxes)
        plt.text(0.02, 0.75,r'z={:.2f}'.format(z), color='k',fontsize=20,transform=ax.transAxes)
        #add_text_to_ax(0.05, 0.95-2*textsep, r'log($L_I$$_R$)={:.2f}'.format(np.log10(Lir_total)),ax=ax,fontsize=20, color='k')
        #add_text_to_ax(0.05, 0.95-3*textsep, r'log($M_d$)={:.2f}'.format(np.log10(Mdust)),ax=ax,fontsize=20, color='k')

        ylabel(r'$f_{\nu}$ [mJy]',fontsize=25)
        xlabel(r'$\lambda_{obs}$ $[\mu m]$',fontsize=25)
        legend(fontsize=12)
        ylim(10**-4,10**3)
        xlim(.5,10**5.7)
        grid(alpha=0.4)
        #ylim(10**-5,10**4)
        #xlim(.1,10**5.7)
        yscale('log')
        xscale('log')
        plt.tight_layout()
        plt.savefig('sed_example_new_code.pdf')

        if save_fig:
            plt.savefig(figloc + str(int(P[galaxy_index,0])) + ".pdf")
        if diagplot:
            show()

    #----------------------------------------------------------------------------------------

    if verbose:
        print('------------------------------------------')
        print ('Finished fitting ID:',P[galaxy_index,0])
        print('------------------------------------------')

    R=np.array([int(P[galaxy_index,0]),Lir_total,eLir_total,Mdust,eMD,z,chi2red_nnls,fagn,efagn,
    lastdet,ztype[galaxy_index],Mgas,eMG,deltaGDR,attempt,Mstar,100*Mdust/Mstar,
    Mgas/Mstar,Lir_med,Lir_med_err,Mdust_med,Mdust_med_err,Umin[minsol[0]],minsol[1],
    g[minsol[2]],U,sU,Lagn,eLagn,Lir_draine,eLir_draine])
    nnsol=np.array(nnsol)



    if save_table:
        att=0
        while att<100:
            try:
                time.sleep(np.random.uniform(1,3))
                t0=Table.read(table_out)
                t0.add_row(R)
                t0.write(table_out,overwrite=True)
                break
            except:
                att+=1
                time.sleep(3)



    return None


objects=range(len(G[:,0]))

if not multithread:
    for i,obj in enumerate(objects):
        galproc(i)
    sys.exit()


objects=range(len(G[:,0]))
from multiprocessing import Pool
from multiprocessing import Process
import multiprocessing


if multithread:
    print('Begin multithreading')
    pool = Pool(multiprocessing.cpu_count())
    print(multiprocessing.cpu_count(),'threads utilised')                    # Create a multiprocessing Pool
    mp_out= np.array(pool.map(galproc,objects))
    mp_out=np.array(mp_out)
    print ('Code took',time.time()-timer_start, 's to run')


if save_table:
    table_final=Table.read(table_out)
    #table_final=table_final[table_final['ID']!=0] #Remove placeholder row
    table_final=table_final[1:] #Remove placeholder row
    table_final.write(table_out,overwrite=True)

sys.exit()
