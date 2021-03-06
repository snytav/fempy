import numpy as np
import fempy as fp

import mayavi.mlab as mlab
from mayavi import mlab 
#import tvtk.api as tvtk
from tvtk.api import tvtk, write_data

import pdb

class VtkDataUnstruct(object):
    
    def __init__(self,node,element):
        self.SetGrid(node,element)
    
    def SetGrid(self,node,element):
            
        if type(node) != fp.basic.NodeArray:
            node = fp.NodeArray(narray=node)
   
        self.numElem = len(element)
        self.numNode = len(node)
        
        nidmap = node.ContinousNIDMap()
        
        # generate the VTK cell data.  This is a linear array of integers
        # where the first number in a pattern is the number of nodes in the 
        # connectivity followed by the connectivity
        cellSize = 0  # find the size of cells
        for e in element.values():
            cellSize = cellSize + e.NumNodes() + 1
            
        cell = np.zeros( cellSize, dtype=fp.INDX_TYPE )
        offset = np.zeros( self.numElem, dtype=fp.INDX_TYPE )
        cell_type = np.zeros( self.numElem, dtype=fp.INDX_TYPE )
        
        n = 1
        en = 0
        for e in element.values():
        
            nn = e.NumNodes()
            cell[n-1] = nn
            for i in xrange(nn):
                cell[n+i] = nidmap[ e.conn[i] ] 
        
            offset[en]= n-1
                    
            if ( e.Type() == 'LINE2' ):
                cell_type[en] = 3
            elif ( e.Type() == 'LINE3' ): 
                cell_type[en] = 21  
            elif ( e.Type() == 'TRIA3' ): 
                cell_type[en] = 5
            elif ( e.Type() == 'TRIA6' ): 
                cell_type[en] = 22 
            elif ( e.Type() == 'QUAD4' ): 
                cell_type[en] = 9
            elif ( e.Type() == 'QUAD8' ): 
                cell_type[en] = 23
            elif ( e.Type() == 'TETRA4' ): 
                cell_type[en] = 10
            elif ( e.Type() == 'TETRA10' ): 
                cell_type[en] = 24
            elif ( e.Type() == 'HEXA8' ): 
                cell_type[en] = 12
            elif ( e.Type() == 'HEXA20' ): 
                cell_type[en] = 25
            elif ( e.Type() == 'POINT1' ): 
                cell_type[en] = 1
                
            n = n + nn + 1
            en = en + 1
        
        cell_array = tvtk.CellArray()
        cell_array.set_cells(self.numElem, cell)
        
        points = np.zeros( (self.numNode,3), dtype=fp.FLOAT_TYPE )
        i=0
        for n in node.iteritems():
            points[i,:] = n[1]
            i += 1
        
        self.ugdata = tvtk.UnstructuredGrid(points=points)
        
        # Now just set the cell types and reuse the ug locations and cells.
        self.ugdata.set_cells(cell_type, offset, cell_array)   
    
    def GetVtkData(self):
        return self.ugdata
    
    def AddNodeScalarField(self,svar,sname):
        self.ugdata.point_data.scalars = svar
        self.ugdata.point_data.scalars.name = sname
        
    def AddNodeVectorField(self,vvar,vname):
        if ( vvar.ndim == 1 ):
            nn = len(vvar)/3
            vvar = np.reshape( vvar, (nn,3) )
        self.ugdata.point_data.vectors = vvar
        self.ugdata.point_data.vectors.name = vname
        
    def AddCellScalarField(self,svar,sname):
        self.ugdata.cell_data.scalars = svar
        self.ugdata.cell_data.scalars.name = sname
    
    def PlotScalar(self):
        mlab.clf()
        mlab.pipeline.surface(self.ugdata)

    def WriteVtkFile(self,filename):
        write_data( self.ugdata, filename )
        
class FeaData(VtkDataUnstruct):
    
    def __init__(self,node,element):
        self.SetGrid(node,element)
        
    def SetDisplacement(self,d,dofmap,sdim=3):
        nn = len(self.ugdata.points)
        dv = np.zeros( (nn,3), fp.FLOAT_TYPE )
        for s in xrange(sdim):
            for i in xrange(nn):
                ii = dofmap.GID(i,s)
                dv[i,s] = d[ii]
        self.ugdata.point_data.vectors = dv
        self.ugdata.point_data.vectors.name = 'Displacement'
        
    def SetEffectiveStress(self,svm,stype='Mises Stress'):
        
        self.ugdata.cell_data.scalars = svm
        self.ugdata.cell_data.scalars.name = stype
        
    def SetStress(self,sig):
        sdim = sig.shape[1]
        ne = self.numElem
        stress = np.zeros( (ne,9), fp.FLOAT_TYPE )
        for i in xrange(sdim):
            stress[:,i] = sig[:,i]
        self.ugdata.cell_data.tensors = stress
        self.ugdata.cell_data.tensors.name = 'Stress'
        
    def SetData(self,d,dofmap,sdim=3,sig=None,svm=None):
        self.SetDisplacement(d,dofmap,sdim)
        if ( not sig==None ):
            self.SetStress(sig)
        if ( not svm==None ):
            self.SetEffectiveStress(svm)
                    
class ParticleData(VtkDataUnstruct):
    
    def __init__(self,pts=None):
        if pts!=None:
            self.SetPoints(pts)
    
    def SetPoints(self,pts):
            
        self.numNode = len(pts)
        
        #points = np.zeros( (self.numNode,3), dtype=fp.FLOAT_TYPE )
        #points[:,:pts.shape[1]] = pts
        
        #self.ugdata = tvtk.UnstructuredGrid(points=points)   
        
        conn = fp.ElementArray( 
             conn=np.array([range(self.numNode)],dtype=int).transpose(),
             etype=fp.ElemPoint1 )
        self.SetGrid(pts,conn)
    
    def SetParticleData(self,d,x,v):
        self.SetPoints(x)
        self.AddNodeScalarField(d,'Diameter')
        self.AddNodeVectorField(v,'Velocity')

    def WriteVtkFile(self,job,step=0):
        write_data( self.ugdata, job+str(step).zfill(4)+'.vtu' )    
    