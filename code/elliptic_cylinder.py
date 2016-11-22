import numpy as np
from scipy import linalg

from fatiando import mesher, gridder, utils

import scipy.special

def elliptic (xp,yp,zp,xc,yc,zc,b,c,delta,declirem,inclirem,intensity,decT,incT,intT,k):
    '''
    Calculates the three componentes of magnetic field generated by an elliptic cylinder.
    
    input:
    xp,yp - Origin of the elliptic cylinder in the geographic coordinate.
    zp - Depth of the the elliptic cylinder.
    a,b - Major and minor axis, respectively.
    delta - Inclination between the major-axe and the horizontal plane (0<=delta<=90, radians).
    xc,yc,zc - point in the grid that has the center of the elliptic cylinder.
    declirem - declination of the remanent vector.
    inclirem - inclination of the remanent vector.
    intensity - intensity of the remanent vector.
    intT - Intensity of the Earth's magnetic field.
    incT - Inclination of the Earth's magnetic field.
    decT - Declination of the Earth's magnetic field.
    k - 3x3 matrix where each line has the intensity, declination and inclination of the three susceptibilities vectors.
    
    output:
    Bx_P, Bz_P, Tf_P - components of magnetic field generated by an elliptic cylinder and the total-field anomaly.
    '''
    
    center = np.array([xc,yc,zc])
    axis = np.array([b,c])
    
    delta = np.deg2rad(delta)
    angles = np.array([delta])
    
    mcon, mconT = m_conv(angles)
    
    declirem = np.deg2rad(declirem)
    inclirem = np.deg2rad(inclirem)
    
    ln,mn,nn = lmnn_v (declirem, inclirem)
    
    decT = np.deg2rad(decT)
    incT = np.deg2rad(incT)
    
    lt,mt,nt = lmnn_v (decT, incT)

    k_int = np.array([k[0][0],k[1][0],k[2][0]])
    k_inc = np.array([k[0][1],k[1][1],k[2][1]])
    k_dec = np.array([k[0][2],k[1][2],k[2][2]])
    
    if k_int[0] == (k_int[1] and k_int[2]):
        km = k_matrix(k_int,mcon)
    else:
        km = k_matrix2(k_int,mcon)

    # Magnetizacoes nas coordenadas do elliptic cylindere
    F = F_e (intT,lt,mt,nt,mcon)
    JN = JN_e (intensity,ln,mn,nn,mcon)
    N2,N3 = N_desmag (axis)
    JR = JR_e (km,JN,F)
    JRD = JRD_e (km,N2,N3,JR)
    JRD_carte = (mconT).dot(JRD)
    JRD_ang = utils.vec2ang(JRD_carte)
    
    # Coordenadas Cartesianas elliptic cylindere
    x2,x3 = x_e (xp,yp,zp,center,mcon)

    # Calculos auxiliares
    r = r_e (x2,x3)
    delta = delta_e (axis,r,x2,x3)

    # Raizes da equacao cubica
    lamb = lamb_e (axis,r,delta)

    # Derivadas de lambda em relacao as posicoes
    dlambx2, dlambx3 = dlambx_e (axis,r,x2,x3,lamb,delta)
    
    # Calculos auxiliares do campo
    f1 = f1_e (axis,x2,x3,lamb,JRD)
    
    # Problema Direto (Calcular o campo externo nas coordenadas do elliptic cylindere)
    B2 = B2_e (dlambx2,lamb,JRD,f1,axis)
    B3 = B3_e (dlambx3,lamb,JRD,f1,axis)
    
    # Problema Direto (Calcular o campo externo nas coordenadas geograficas)
    Bx = Bx_c (B2,B3,mcon[1,0],mcon[2,0])
    Bz = Bz_c (B2,B3,mcon[1,2],mcon[2,2])
    
    Tf = (Bx*np.cos(incT)*np.cos(decT) + Bz*np.sin(incT))
    
    return Bx, Bz, Tf
    
def m_conv (angles):
    '''
    Builds the matrix of coordinate system change to the center of the elliptic cylinder. Used for the triaxial 
    and prolate elliptic cylinders.
        
    input:
    alpha - Azimuth+180 degrees in relation to the major-axe and the geographic north (0<=alpha<=360, radians).
    delta - Inclination between the major-axe and the horizontal plane (0<=delta<=90, radians).
    gamma - Angle between the intermediate-axe and the vertical projection of the horizontal plane to the
    center of the elliptic cylinder(radians).
      
    output:
    A 3x3 matrix.
    '''
    mcon = np.zeros((3,3))
    mcon[0][0] = (0)
    mcon[1][0] = (np.cos(angles[0]))
    mcon[2][0] = (-np.sin(angles[0]))
    mcon[0][1] = (1.)
    mcon[1][1] = (0.)
    mcon[2][1] = (0.)
    mcon[0][2] = (0.)
    mcon[1][2] = (-np.sin(angles[0]))
    mcon[2][2] = (-np.cos(angles[0]))
    mconT = (mcon).T
    return mcon, mconT
    
def lmnn_v (dec, inc):

    '''
    Calculates de direction cosines of a vector.
    
    input:
    inc - Inclination.
    dec - Declination.
    
    output:
    ln,mn,nn - direction cosines.    
    '''
    
    ln = (np.cos(dec)*np.cos(inc))
    mn = (np.sin(dec)*np.cos(inc))
    nn = np.sin(inc)
    return ln, mn, nn
    
def F_e (intT,lt,mt,nt,mcon):
    '''
    Change the magnetization vetor of the Earth's field to the body coordinates.
    
    input:
    inten - Intensity of the Earth's magnetic field.
    lt,mt,nt - direction cosines of the Earth's magnetic field.
    l1,l2,l3,m1,m2,m3,n1,n2,n3 - matrix of body coordinates change.
    
    output:
    Ft - The magnetization vetor of the Earth's field to the body coordinates.    
    '''
    F = intT*np.array([[(lt*mcon[0,0]+mt*mcon[0,1]+nt*mcon[0,2])], [(lt*mcon[1,0]+mt*mcon[1,1]+nt*mcon[1,2])], [(lt*mcon[2,0]+mt*mcon[2,1]+nt*mcon[2,2])]])
    return F
    
def JN_e (intensity,ln,mn,nn,mcon):
    '''
    Changes the remanent magnetization vector to the body coordinate.
        
    input:
    intensity - intensity of remanent vector.
    ln,nn,mn - direction cosines of the remanent magnetization vector.
    mcon - matrix of conversion.
        
    output:
    JN - Remanent magnetization vector in the body coordinate.         
    '''
    JN = intensity*np.array([[(ln*mcon[0,0]+mn*mcon[0,1]+nn*mcon[0,2])], [(ln*mcon[1,0]+mn*mcon[1,1]+nn*mcon[1,2])], [(ln*mcon[2,0]+mn*mcon[2,1]+nn*mcon[2,2])]])
    return JN

def N_desmag (axis):
    '''
    Calculates the three demagnetization factor along major, intermediate and minor axis. For the prolate elliptic cylinder use.
        
    input:
    b,c - Major and minor axis, respectively.
      
    output:
    N2, N3 - Major and minor demagnetization factors, respectively.        
    '''
    
    N2 = (4*np.pi*axis[1])/(axis[0]+axis[1])
    N3 = (4*np.pi*axis[0])/(axis[0]+axis[1])
    return N2, N3
    
def k_matrix (k_int,mcon):
    '''
    Build susceptibility tensors matrix for the isotropic case in the body coordinates.
        
    input:
    mcon - Matrix of conversion.
    k_int - Intensity of the three directions of susceptibility.
        
    output:
    km - Susceptibility tensors matrix.        
    '''
        
    km = np.zeros([3,3])
    for i in range (3):
        for j in range (3):
            for r in range (3):
                km[i,j] = km[i,j] + (k_int[r]*(mcon[r,0]*mcon[i,0] + mcon[r,1]*mcon[i,1] + mcon[r,2]*mcon[i,2])*(mcon[r,0]*mcon[j,0] + mcon[r,1]*mcon[j,1] + mcon[r,2]*mcon[j,2]))
    return km

def k_matrix2 (k_int,mcon):
    '''
    Build the susceptibility tensors matrix for the anisotropic case in the body coordinates.
        
    input:
    mcon - Matrix of conversion.
    k_int - Intensity of the three directions of susceptibility.
        
    output:
    km - Susceptibility tensors matrix.        
    '''
        
    Lr = np.zeros(3)
    Mr = np.zeros(3)
    Nr = np.zeros(3)
    for i in range (3):
        Lr[i] = np.cos(k_dec[i])*np.cos(k_inc[i])
        Mr[i] = np.sin(k_dec[i])*np.cos(k_inc[i])
        Nr[i] = np.sin(k_inc[i])
    km = np.zeros([3,3])
    for i in range (3):
        for j in range (3):
            for r in range (3):
                km[i,j] = km[i,j] + (k_int[r]*(Lr[r]*mcon[i,0] + Mr[r]*mcon[i,1] + Nr[r]*mcon[i,2])*(Lr[r]*mcon[j,0] + Mr[r]*mcon[j,1] + Nr[r]*mcon[j,2]))
    return km
    
def JR_e (km,JN,F):
    '''
    Calculates the resultant magnetization vector without self-demagnetization correction.
    
    input:
    km - matrix of susceptibilities tensor.
    JN - Remanent magnetization
    Ft - Magnetization vetor of the Earth's field in the body coordinates.
    
    output:
    JR - Resultant magnetization vector without self-demagnetization correction.   
    '''
    
    JR = km.dot(F) + JN
    return JR
    
def JRD_e (km,N2,N3,JR):
    '''
    Calculates resultant magnetization vector with self-demagnetization correction.
    
    input:
    km - matrix of susceptibilities tensor.
    N1,N2,N3 - Demagnetization factors in relation to a, b and c, respectively.
    JR - resultant magnetization vector without self-demagnetization correction.
    
    output:
    JRD - Resultant magnetization vector without self-demagnetization correction.    
    '''
    
    I = np.identity(3)
    kn0 = km[:,0]*0
    kn1 = km[:,1]*N2
    kn2 = km[:,2]*N2
    kn = (np.vstack((kn0,kn1,kn2))).T
    A = I + kn
    JRD = (linalg.inv(A)).dot(JR)
    return JRD

def x_e (xp,yp,zp,center,mcon):
    '''
    Calculates the new coordinates with origin at the center of the elliptic cylinder.

    input:
    xp,yp - Origin of the elliptic cylinder in the geographic coordinate.
    zp - Depth of the the elliptic cylinder.
    center - point in the grid that has the center of the elliptic cylinder.
    mcon - Matrix of conversion.
        
    output:
    x2, x3 - The three axes of the coordinates.
    '''

    x2 = (xp-center[0])*mcon[1,0]+(yp-center[1])*mcon[1,1]-(zp+center[2])*mcon[1,2]
    x3 = (xp-center[0])*mcon[2,0]+(yp-center[1])*mcon[2,1]-(zp+center[2])*mcon[2,2]
    return x2, x3

def r_e (x2,x3):
    '''
    Calculates the distance between the observation point and the center of the elliptic cylinder.
    Used in the prolate and oblate elliptic cylinders.
      
    input:
    x2, x3 - Axis of the body coordinate system.
      
    output:
    r - Distance between the observation point and the center of the elliptic cylinder.        
    '''
    
    r = ((x2)**2+(x3)**2)**0.5
    return r
    
def delta_e (axis,r,x2,x3):
    '''
    Calculates an auxiliar constant for lambda.
        
    input:
    b, c - Major, intermediate and minor axis, respectively.
    r - Distance between the observation point and the center of the elliptic cylinder.
    x2, x3 - Axis of the body coordinate system.
       
    output:
    delta - Auxiliar constant for lambda.        
    '''

    delta = (r**4 + (axis[0]**2-axis[1]**2)**2 - 2*(axis[0]**2-axis[1]**2) * (x2**2 - x3**2))**0.5
    return delta    
    
def lamb_e (axis,r,delta):
    '''
    Calculates the Larger root of the cartesian elliptic cylinderal equation.
    Used in the prolate elliptic cylinders.
      
    input:
    b, c - Major, intermediate and minor axis, respectively.
    delta - Auxiliar constant for lambda.
    r - Distance between the observation point and the center of the elliptic cylinder.
     
    output:
    lamb - Larger root of the cartesian elliptic cylinderal equation.
    '''
    
    lamb = (r**2 - axis[0]**2 - axis[1]**2 + delta)/2.
    return lamb

def dlambx_e (axis,r,x2,x3,lamb,delta):
    '''
    Calculates the derivatives of the elliptic cylinder equation for each body coordinates in realation to lambda.
    Used for the prolate elliptic cylinders.
    
    input:
    b, c - Major, intermediate and minor axis, respectively.
    x2, x3 - Axis of the body coordinate system.
    delta - Auxiliar constant for lambda.
    lamb - Larger root of the cartesian elliptic cylinderal equation.
    r - Distance between the observation point and the center of the elliptic cylinder.
    
    output:
    dlambx1,dlambx2,dlambx3 - Derivatives of the elliptic cylinder equation for each body coordinates in realation to x1,x2 and x3.        
    '''
    
    dlambx2 = x2*(1+((r**2-axis[0]**2+axis[1]**2)/delta))
    dlambx3 = x3*(1+((r**2+axis[0]**2-axis[1]**2)/delta))
    return dlambx2, dlambx3

def f1_e (axis,x2,x3,lamb,JRD):
    '''
    Auxiliar calculus of magnetic field generated by a prolate elliptic cylinder.

    input:
    b,c - Major and minor axis, respectively.
    x2,x3 - Axis of the body coordinate system.
    lamb - Larger root of the cartesian elliptic cylinderal equation.
    JRD - Resultant magnetization vector with self-demagnetization correction.
    
    output:
    f1 - Auxiliar calculus of magnetic field generated by a prolate or an oblate elliptic cylinder.
    '''
    
    f1 = ((2*np.pi*axis[0]*axis[1])/((axis[0]**2+lamb)*(axis[1]**2+lamb))**0.5) * (((JRD[1]*x2)/(axis[0]**2+lamb)) + ((JRD[2]*x3)/(axis[1]**2+lamb)))
    return f1

def B2_e (dlambx2,lamb,JRD,f1,axis):
    '''
    Calculates the B2 component of the magnetic field generated by n-elliptic cylinders in the body coordinates.
    Used in the prolate elliptic cylinder.
    
    input:
    dlambx2 - Derivative of the elliptic cylinder equation for each body coordinates in realation to x2.
    JRD - Resultant magnetization vector with self-demagnetization correction.
    f1 - Auxiliar calculus of magnetic field generated by a prolate elliptic cylinder.
    lamb - Larger root of the cartesian elliptic cylinderal equation.
    
    output:
    B2 - The B2 component of the magnetic field generated by n-elliptic cylinders in the body coordinates.
    '''
    
    B2 = (dlambx2*f1) - ((4.*np.pi*axis[0]*axis[1])/(axis[0]**2-axis[1]**2)) * JRD[1] * (1. - ((axis[1]**2+lamb)/(axis[0]**2+lamb))**0.5)
    return B2
    
def B3_e (dlambx3,lamb,JRD,f1,axis):
    '''
    Calculates the B3 component of the magnetic field generated by n-elliptic cylinders in the body coordinates.
    Used in the prolate elliptic cylinders.
    
    input:
    dlambx3 - Derivative of the elliptic cylinder equation for each body coordinates in realation to x3.
    JRD - Resultant magnetization vector with self-demagnetization correction.
    f1 - Auxiliar calculus of magnetic field generated by a prolate elliptic cylinder.
    lamb - Larger root of the cartesian elliptic cylinderal equation.
    
    output:
    B3 - The B3 component of the magnetic field generated by n-elliptic cylinders in the body coordinates.
    '''
    
    B3 = (dlambx3*f1) - ((4.*np.pi*axis[0]*axis[1])/(axis[0]**2-axis[1]**2)) * JRD[2] * (((axis[0]**2+lamb)/(axis[1]**2+lamb))**0.5 - 1.)
    return B3
    
def Bx_c (B2,B3,l2,l3):
    '''
    Change the X component of the magnetic field generated by n-elliptic cylinders to the cartesian coordinates.
    
    input:
    B2,B3 - Components of the magnetic field generated by n-elliptic cylinders to the body coordinates.
    l2,l3 - Direction cosines for coordinates change.
    
    output:
    Bz - The X component of the magnetic field generated by n-elliptic cylinders to the cartesian coordinates.
    '''
    
    Bx = B2*l2+B3*l3
    return Bx
    
def Bz_c (B2,B3,n2,n3):
    '''
    Change the Z component of the magnetic field generated by n-elliptic cylinders to the cartesian coordinates.
    
    input:
    B2,B3 - Components of the magnetic field generated by n-elliptic cylinders to the body coordinates.
    n2,n3 - Direction cosines for coordinates change.
    
    output:
    Bz - The Z component of the magnetic field generated by n-elliptic cylinders to the cartesian coordinates.
    '''
    
    Bz = B2*n2+B3*n3
    return Bz