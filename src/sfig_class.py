# class stress factor
# class intergranular strain
from MP.mat import mech
import numpy as np
fc = mech.FlowCurve
sin = np.sin
cos = np.cos
from MP.lib import mpl_lib
wide_fig = mpl_lib.wide_fig
from RS import rs
interp = rs.interpolate

class SF:
    def __init__(self):
        pass
    def add_data(self,sf=None,phi=None,psi=None):
        """
        sf[nstp,nphi,npsi,nij]
        """
        self.flow = fc()
        if sf!=None:
            self.sf  = sf
            self.sf.shape
            # if len(self.sf.shape)!=4:
            #     self.sf = np.array([self.sf])
            self.nstp = len(self.sf[0])

            self.nij = self.sf.shape[-1]
            if self.nij!=6: print 'Stress factor'+\
               ' is not fully given in 6D'

        if phi!=None:
            self.phi = phi
            self.nphi = len(self.phi)
        if psi!=None:
            self.psi = psi
            self.sin2psi = np.sin(self.psi*np.pi/180.)**2
            self.npsi = len(self.psi)

    def add_vf(self,vf): self.vf = vf[::]

    def add_rsq(self,rsq): self.rsq = rsq[::]

    def add_flow(self,eps,i,j):
        self.flow.get_strain(eps,i,j)

    def get_iso_sf(self,E,nu):
        self.add_iso_sf(E=E,nu=nu)
        sf_new = np.zeros(self.sf.shape)
        sf_new[:] = self.sf_iso.copy()
        self.sf_old = self.sf.copy()
        self.sf = sf_new.copy()

    def restore_sf(self):
        """ Restore self.sf_old to self.sf """
        self.sf = self.sf_old.copy()

    def add_iso_sf(self,E=204e9,nu=0.3):
        phi = self.phi.copy()
        psi = self.psi.copy()
        self.sf_iso = np.zeros((len(phi),len(psi),6))
        for iphi in range(len(phi)):
            for ipsi in range(len(psi)):
                self.sf_iso[iphi,ipsi] = calc_iso_sf(
                    phi=phi[iphi],psi=psi[ipsi],
                    nu=nu,Y=E,iopt=1).copy()
    def reduce_psi(
            self, bounds = [0.0,0.5],
            ntot_psi = 17):
        self.bound_psi(bounds = bounds)
        self.reso_psi(ntot=ntot_psi)

    def bound_psi(self, bounds = [0.0,0.5]):
        from rs import filter_psi2 as filter_psi
        sft = self.sf.swapaxes(-1,-2)
        psi_dum = self.psi[::]

        ## bounds filter
        sft = filter_psi(
            obj=sft[::], sin2psi=self.sin2psi[::],
            bounds=bounds)
        if hasattr(self, 'vf'):
            vf = filter_psi(
                obj=self.vf[::],sin2psi=self.sin2psi[::],
                bounds=bounds)
        if hasattr(self, 'rsq'):
            rsq = filter_psi(
                obj=self.rsq[::],sin2psi=self.sin2psi[::],
                bounds=bounds)
        sin2psi = filter_psi(
            obj=self.sin2psi[::],sin2psi=self.sin2psi[::],
            bounds=bounds)
        psid = filter_psi(
            obj=psi_dum[::],sin2psi=self.sin2psi[::],
            bounds=bounds)

        self.sf=sft.swapaxes(-1,-2)
        self.sin2psi = sin2psi[::]
        self.psi = psid[::]
        self.npsi = len(self.psi)
        if hasattr(self, 'vf'): self.vf=vf[::]
        if hasattr(self, 'rsq'): self.rsq=rsq[::]

    def reso_psi(self,ntot=17):
        from rs import psi_reso3 as reso
        sft = self.sf.swapaxes(-1,-2)
        psid = self.psi[::] * np.pi/180.
        sin2psi = self.sin2psi[::]

        # ## psi reduce resol.
        sft = reso(obj=sft[::], psi=psid[::],ntot=ntot)
        if hasattr(self, 'vf'):
            vf = reso(obj=vf[::], psi=psid[::],ntot=ntot)
        if hasattr(self, 'rsq'):
            rsq = reso(obj=rsq[::], psi=psid[::],ntot=ntot)

        sin2psi = reso(obj=sin2psi[::], psi=psid[::],ntot=ntot)
        psi = reso(obj=psid[::], psi=psid[::],ntot=ntot)

        self.sf = sft.swapaxes(-1,-2)
        print self.sf.shape
        self.sin2psi = sin2psi[::]
        self.psi = psi[::] * 180./np.pi
        self.npsi = len(self.psi)
        if hasattr(self, 'vf'): self.vf=vf[::]
        if hasattr(self, 'rsq'): self.rsq=rsq[::]

    def interp_strain(self,epsilon_vm):
        """
        Linearly interpolate the SF with respect to
        the given VM strain

        Arguments
        =========
        epsilon_vm = []
        """
        self.sf_old = self.sf.copy()
        # self.flow.get_vm_strain()
        # self.flow.epsilon_vm #
        self.sf_new = np.zeros(
            (len(epsilon_vm),self.nphi,self.npsi,self.nij))
        for iphi in range(self.nphi):
            for ipsi in range(self.npsi):
                for k in range(self.nij):
                    y = self.sf_old[:,iphi,ipsi,k]
                    self.sf_new[:,iphi,ipsi,k] = interp(
                        epsilon_vm,self.flow.epsilon_vm,y)

        self.sf = self.sf_new
        # Overwrite the flow? self.nstp also needs change
        self.flow = fc()
        self.flow.epsilon_vm = np.array(epsilon_vm)
        self.nstp = len(self.flow.epsilon_vm)

    def interp_psi(self,psi=None,iopt=1):
        """
        iopt=0: interpolate along psi
        iopt=1: interpolate along +- sin2psi
        """
        psi = np.array(psi)
        from numpy import sign
        if iopt==0:
            x = psi
            x0 = self.psi
        if iopt==1:
            x = sign(psi) * sin(psi*np.pi/180.)**2
            x0 = sign(self.psi) * sin(self.psi*np.pi/180.)**2

        self.sf_old = self.sf.copy()
        self.psi_old = self.psi.copy()
        self.npsi # also need change

        self.sf_new = np.zeros(
            (self.nstp,self.nphi,len(x),self.nij))
        for istp in range(self.nstp):
            for iphi in range(self.nphi):
                for k in range(self.nij):
                    y = self.sf_old[istp,iphi,:,k]
                    self.sf_new[istp,iphi,:,k] = interp(
                        x,x0,y)

        self.sf = self.sf_new.copy()
        self.psi = psi.copy()
        self.npsi = len(self.psi)

    def change_phi(self,phi):
        """
        """
        self.sf_old = self.sf.copy()
        self.phi_old = self.phi.copy()
        self.nphi # also need change
        pass

    def determine_phis(self,phi_new):
        deg = 180./np.pi
        nphi = self.nphi
        npsi = self.npsi
        nstp = self.flow.nstp
        phi_old = self.phi.tolist()
        nphi_new = len(phi_new)
        ind = []

        for i in range(len(phi_new)):
            try:
                j = phi_old.index(phi_new[i])
            except ValueError:
                #print i
                #print 'Mirror?'
                #print 'Is this okay to set -phi = phi?'
                #print 'Warning!!!> Go ahead only',
                #print ' if you know what you are getting to'
                j = phi_old.index(abs(phi_new[i]))
                ind.append(j)
            else: ind.append(j)

        sf_new = np.zeros((
            self.nstp,nphi_new,self.npsi,self.nij))

        for i in range(len(ind)):
            sf_new[:,i,:,:] = self.sf[:,ind[i],:,:]
        self.sf = sf_new.copy()
        self.phi = np.array(phi_new)
        self.nphi = len(self.phi)

    def mask_vol(self,pmargin=0.05):
        """
        1) Mask data in case that volume (ngr) is zero
        2) Or, if self.vf is given, use proportional margin
           to set a limit for indivial plastic level
        """
        if hasattr(self, 'vf'):
            print 'self has vf property.',\
                ' Do mask based on volume margin:',\
                ' %5.3f%%'%(pmargin*100)
            ntot = 0
            for istp in range(self.nstp):
                n = 0
                for iphi in range(self.nphi):
                    mean  = np.mean(self.vf[istp,iphi,:])
                    limit = mean*pmargin
                    print 'mean and limit:', mean, limit
                    for ipsi in range(self.npsi):
                        if self.vf[istp,iphi,ipsi]<limit:
                            self.sf[istp,iphi,ipsi,:] = np.nan
                            n = n + 1
                print '%i number of sf data points were masked for step %i'%(n,istp)
                ntot = ntot + n
            print '%i number of sf data points were masked in total'%ntot

                    ##self.sf[istp,iphi,:,:][self.vf[istp,iphi,:]<limit]=np.nan
        else:
            print 'No volume is given. Mask if sf==0'
            self.sf[self.sf==0]=np.nan

    def mask_vol_abs(self,value=0.001):
        self.sf[self.sf<value]=np.nan

    def plot(self,nbin_sin2psi=2,iopt=0,ylim=None,
             mxnphi=None,hkl='211'):
        """   """
        from MP.lib import axes_label
        from MP.lib import mpl_lib
        import matplotlib as mpl
        import matplotlib.cm as cm
        if hasattr(self, 'vf'):
            nh = 2
        else: nh = 1

        if mxnphi==None: mxnphi = self.nphi
        figs = wide_fig(nw=mxnphi,nh=nh,w0=0,w1=0,
                        left=0.2,right=0.15)

        mx = max(self.flow.epsilon_vm)
        mn = min(self.flow.epsilon_vm)
        # mx = 1.
        # mn = 0.
        cmap, c = mpl_lib.norm_cmap(mx=mx,mn=mn)
        colors=[]
        self.flow.nstp = len(self.flow.epsilon_vm)
        for i in range(mxnphi):
            for j in range(self.flow.nstp):
                eps = self.flow.epsilon_vm[j]
                cl = c.to_rgba(eps)
                if i==0: colors.append(cl)

                y = self.sf[j,i,:,0] * 1e12
                l, = figs.axes[i].plot(
                    np.sign(self.psi)*sin(self.psi*np.pi/180.)**2,
                    y,'-x',color=cl)
                y = self.sf[j,i,:,1] * 1e12
                figs.axes[i].plot(
                    np.sign(self.psi)*sin(self.psi*np.pi/180.)**2,
                    y,'--.',color=cl)

                if j==0:
                    figs.axes[i].set_title(
                        r'$\phi: %3.1f^\circ{}$'%self.phi[i])

        if nh==2:
            for i in range(mxnphi):
                for j in range(self.flow.nstp):
                    eps = self.flow.epsilon_vm[j]
                    cl = c.to_rgba(eps)
                    y = self.vf[j,i,:]
                    figs.axes[i+mxnphi].plot(
                        np.sign(self.psi)*sin(self.psi*np.pi/180.)**2,
                        y,'-',color=cl)

        deco = axes_label.__deco__
        rm_inner =mpl_lib.rm_inner
        ticks_bin_u = mpl_lib.ticks_bins_ax_u
        rm_inner(figs.axes[:mxnphi])
        if nh==2: rm_inner(figs.axes[mxnphi:mxnphi*2])
        deco(figs.axes[0],iopt=1,ipsi_opt=1,hkl=hkl)
        if nh==2: deco(figs.axes[mxnphi],iopt=7,ipsi_opt=1,hkl=hkl)
        mpl_lib.tune_xy_lim(figs.axes[:mxnphi])
        if ylim!=None:
            for i in range(len(figs.axes[:mxnphi])):
                figs.axes[i].set_ylim(ylim)
        if nh==2: mpl_lib.tune_xy_lim(figs.axes[mxnphi:mxnphi*2])
        ticks_bin_u(figs.axes[:mxnphi],n=4)
        if nh==2: ticks_bin_u(figs.axes[mxnphi:mxnphi*2],n=4)

        # color bar
        b = figs.axes[-1].get_position()
        axcb = figs.add_axes([0.88,b.y0,0.03,b.y1-b.y0])
        mpl_lib.add_cb(ax=axcb,filled=False,
                       levels=self.flow.epsilon_vm,
                       colors=colors,ylab='Equivalent strain')

        if nh==1: return

        """   SF(phi,psi) vs plastic strain   """
        ## binning sin2psi
        nbin = nbin_sin2psi
        indx = self.__binning__(nbin=nbin,mx=0.5)

        for i in range(len(indx)):
            print '%i bin'%(i+1)
            for j in range(len(indx[i])):
                print '%4i'%indx[i][j],
                print '%4.2f'%(self.sin2psi[indx[i][j]]),
            print


        if mxnphi!=None: mxnphi=self.nphi
        figs_p = wide_fig(nw=mxnphi,nh=nbin,
                          w0=0,w1=0,left=0.2,right=0.15)

        eps = self.flow.epsilon_vm
        for i in range(mxnphi):
            for j in range(nbin):
                ax = figs_p.axes[i+mxnphi*j]
                if j==nbin-1: ax.set_title(
                        r'$\phi: %3.1f^\circ{}$'%self.phi[i])
                idx = indx[j]
                for k in range(len(idx)):
                    y = self.sf[:,i,[idx[k]],0][::]
                    # for n in range(len(y)):
                    #     if np.isnan(y[n])==True:
                    #         raise IOError
                    ax.plot(eps,y,'x')

        for i in range(nbin):
            axes=[]
            for j in range(mxnphi):
                axes.append(figs_p.axes[j+mxnphi*i])
            #mpl_lib.tune_xy_lim(axes)
            if i==0 and j==0:  rm_inner(axes[1:])
            else: rm_inner(axes)

        deco(figs_p.axes[0],iopt=6,hkl=hkl)

        mpl_lib.tune_xy_lim(figs_p.axes)
        #print 'no'
        ticks_bin_u(figs_p.axes,n=3)

        if ylim!=None:
            for i in range(len(figs_p.axes)):
                figs_p.axes[i].set_ylim(ylim)


        if iopt==1:
            for i in range(len(figs.axes)):
                figs.axes[i].set_xlim(0.0,0.5)
            for i in range(3):
                figs.axes[i].set_ylim(-2,2)
                figs.axes[3+i].set_ylim(0.,0.1)


    def __binning__(self,nbin,mx):
        borders = np.linspace(0., mx, nbin+1)
        bounds = []
        indx = []
        for i in range(nbin):
            bounds.append(borders[i:i+2])
            indx.append([])
        ## Find elements along axis psi that belong to
        ## individual bins
        for i in range(nbin):
            mn, mx = bounds[i]
            print 'mn, mx:', mn, mx
            for j in range(self.npsi):
                if mn<=self.sin2psi[j] and self.sin2psi[j]<mx:
                    indx[i].append(j)
        return indx

class IG:
    def add_data(self,ig,phi,psi):
        self.flow = fc()
        #self.ig.shape(nstp,nphi,npsi)
        self.ig = ig
        self.phi=phi
        self.nphi = len(self.phi)
        self.psi=psi
        self.npsi = len(self.psi)
        self.nstp = self.ig.shape[0]
    def add_flow(self,eps,i,j):
        self.flow.get_strain(eps,i,j)
    def interp_strain(self,epsilon_vm):
        self.ig_old = self.ig.copy()
        self.flow.get_vm_strain()
        self.flow.epsilon_vm #
        self.ig_new = np.zeros(
            (len(epsilon_vm),self.nphi,self.npsi))
        for iphi in range(self.nphi):
            for ipsi in range(self.npsi):
                y = self.ig_old[:,iphi,ipsi]
                self.ig_new[:,iphi,ipsi] = interp(
                    epsilon_vm,self.flow.epsilon_vm,y)

        self.ig = self.ig_new
        # Overwrite the flow? self.nstp also needs change
        self.flow = fc()
        self.flow.epsilon_vm = np.array(epsilon_vm)
        self.nstp = len(self.flow.epsilon_vm)
    def interp_psi(self,psi=None,iopt=1):
        """
        iopt=0: interpolate along psi
        iopt=1: interpolate along +- sin2psi
        """
        psi = np.array(psi)
        from numpy import sign
        if iopt==0:
            x = psi
            x0 = self.psi
        if iopt==1:
            x = sign(psi) * sin(psi*np.pi/180.)**2
            x0 = sign(self.psi) * sin(self.psi*np.pi/180.)**2

        self.ig_old = self.ig.copy()
        self.psi_old = self.psi.copy()
        self.npsi # also need change

        self.ig_new = np.zeros(
            (self.nstp,self.nphi,len(x)))
        for istp in range(self.nstp):
            for iphi in range(self.nphi):
                y = self.ig_old[istp,iphi,:]
                self.ig_new[istp,iphi,:] = interp(
                    x,x0,y)

        self.ig = self.ig_new.copy()
        self.psi = psi.copy()
        self.npsi = len(self.psi)

    def determine_phis(self,phi_new):
        deg = 180./np.pi
        nphi = self.nphi
        npsi = self.npsi
        nstp = self.flow.nstp
        phi_old = self.phi.tolist()
        nphi_new = len(phi_new)
        ind = []

        for i in range(len(phi_new)):
            try:
                j = phi_old.index(phi_new[i])
            except ValueError:
                # print i
                # print 'Mirror?'
                # print 'Is this okay to set -phi = phi?'
                # print 'Warning!!!> Go ahead only',
                # print ' if you know what you are getting to'
                j = phi_old.index(abs(phi_new[i]))

                ind.append(j)
            else: ind.append(j)

        ig_new = np.zeros((
            self.nstp,nphi_new,self.npsi))

        for i in range(len(ind)):
            ig_new[:,i,:] = self.ig[:,ind[i],:]
        self.ig = ig_new.copy()
        self.phi = np.array(phi_new)
        self.nphi = len(self.phi)

    def plot(self):
        from MP.lib import axes_label
        from MP.lib import mpl_lib
        import matplotlib as mpl
        import matplotlib.cm as cm

        figs = wide_fig(nw=self.nphi,w0=0,w1=0,
                        left=0.2,right=0.15)

        mx = max(self.flow.epsilon_vm)
        mn = min(self.flow.epsilon_vm)

        cmap, c = mpl_lib.norm_cmap(mx=mx,mn=mn)
        colors=[]
        for i in range(self.nphi):
            for j in range(self.nstp):
                eps = self.flow.epsilon_vm[j]
                cl = c.to_rgba(eps)
                if i==0: colors.append(cl)

                figs.axes[i].plot(
                    np.sign(self.psi)*sin(self.psi*np.pi/180.)**2,
                    self.ig[j,i,:],'-x',color=cl)

                if j==0:
                    figs.axes[i].set_title(
                        r'$\phi: %3.1f^\circ{}$'%self.phi[i])

        deco = axes_label.__deco__
        rm_inner =mpl_lib.rm_inner
        ticks_bin_u = mpl_lib.ticks_bins_ax_u

        deco(figs.axes[0],iopt=2,ipsi_opt=1)
        mpl_lib.tune_xy_lim(figs.axes)
        rm_inner(figs.axes)
        ticks_bin_u(figs.axes,n=4)

        # color bar
        b = figs.axes[-1].get_position()
        axcb = figs.add_axes([0.88,b.y0,0.03,b.y1-b.y0])
        mpl_lib.add_cb(ax=axcb,filled=False,
                       levels=self.flow.epsilon_vm,
                       colors=colors,ylab='Equivalent strain')

def calc_iso_sf(phi,psi,nu,Y,iopt=0):
    """
    Calculate the isotropic elastic stress factor
    iopt=0: return sf[3,3]
    else:   return sf[6]
    """
    phi = phi * np.pi / 180.
    psi = psi * np.pi / 180.

    sin = np.sin
    cos = np.cos

    sf = np.zeros((3,3))
    sf6 = np.zeros((6,))
    nuy = (1. + nu) / Y

    S1 = -nu/Y
    S2 = 2*(1+nu)/Y

    # sf[0,0] = nuy * (sin(psi)**2) * (cos(phi)**2) - nu / Y
    # sf[1,1] = nuy * (sin(psi)**2) * (sin(phi)**2) - nu / Y
    # sf[2,2] = nuy * (cos(psi)**2)                 - nu / Y
    # sf[0,1] = nuy * (sin(psi)**2) * sin(2*phi)
    # sf[0,2] = nuy * sin(2*psi)    * cos(phi)
    # sf[1,2] = nuy * sin(2*psi)    * sin(phi)

    # 2011/JAC/Gnaeupel-Herold, Creuziger, and Iadicola
    sf[0,0] = S1  + 0.5 * S2 * (cos(phi)**2) * (sin(psi)**2)
    sf[1,1] = S1  + 0.5 * S2 * (sin(phi)**2) * (sin(psi)**2)
    sf[2,2] = S1  + 0.5 * S2 *                 (cos(psi)**2)
    sf[0,1] = 0.5 * 0.5 * S2 *  sin(2*phi)   * (sin(psi)**2)
    sf[0,2] = 0.5 * 0.5 * S2 *  cos(phi)     *  sin(2*psi)
    sf[1,2] = 0.5 * 0.5 * S2 *  sin(phi)     *  sin(2*psi)

    # Apply symmetry
    sf[1,0] = sf[0,1]
    sf[2,0] = sf[0,2]
    sf[1,2] = sf[2,1]

    if iopt==0:
        return sf

    from MP.mat import voigt
    vij = voigt.vij
    for i in range(3):
        for j in range(3):
            k = vij[i,j]
            sf6[k] = sf[i,j]

    return sf6
