import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, Any, List, Tuple
import trimesh # Assuming trimesh is available in the environment but not strictly needed in this file
import rtree

class FluidFlowPINN(nn.Module):
    def __init__(self, hidden_dim=256, num_layers=8, fourier_features=64):
        super(FluidFlowPINN, self).__init__()
        
        self.fourier_features = fourier_features
        if fourier_features > 0:
            # Fixed: Initialize B without gradients for Fourier features
            self.register_buffer('B', torch.randn(3, fourier_features, dtype=torch.float32) * 10.0)
        
        # Input: (x, y, z) + fourier features + flow conditions
        input_dim = 3 + (fourier_features * 2 if fourier_features > 0 else 0) + 4
        
        layers = []
        layers.append(nn.Linear(input_dim, hidden_dim))
        layers.append(nn.SiLU())
        
        for _ in range(num_layers - 1):
            layers.append(nn.Linear(hidden_dim, hidden_dim))
            layers.append(nn.SiLU())
        
        layers.append(nn.Linear(hidden_dim, 4))  # Output: u, v, w, p
        
        self.network = nn.Sequential(*layers)
        
        # Ensure model parameters are float32
        self.to(torch.float32)
        
    def fourier_encoding(self, x: torch.Tensor) -> torch.Tensor:
        if self.fourier_features == 0:
            return x
        
        x_proj = 2 * torch.pi * x @ self.B
        return torch.cat([torch.sin(x_proj), torch.cos(x_proj)], dim=-1)
    
    def forward(self, x: torch.Tensor, flow_conditions: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor of shape (batch_size, 3) - spatial coordinates
            flow_conditions: Tensor of shape (batch_size, 4) - [velocity_x, velocity_y, velocity_z, viscosity]
        Returns:
            Tensor of shape (batch_size, 4) - [u, v, w, p]
        """
        # Fourier feature encoding
        fourier_feats = self.fourier_encoding(x)
        
        # Concatenate coordinates, fourier features, and flow conditions
        if self.fourier_features > 0:
            network_input = torch.cat([x, fourier_feats, flow_conditions], dim=-1)
        else:
            network_input = torch.cat([x, flow_conditions], dim=-1)
        
        # Forward pass
        output = self.network(network_input)
        
        return output

class PINNFlowSolver:
    def __init__(self, model_path=None, device='cuda' if torch.cuda.is_available() else 'cpu', model=None):
        self.device = device
        if model is not None:
            self.model = model.to(self.device)
        else:
            self.model = FluidFlowPINN().to(self.device)
        
        if model_path:
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """Load pre-trained model weights"""
        checkpoint = torch.load(model_path, map_location=self.device)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        print(f"Loaded model from {model_path}")
    
    def compute_physics_loss(self, coords: torch.Tensor, predictions: torch.Tensor, 
                           flow_conditions: torch.Tensor, sdf: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Compute physics-informed losses for incompressible Navier-Stokes.
        Uses batch-wise automatic differentiation.
        """
        
        # **Crucial Fix:** Ensure coords require gradients and are part of the computation graph
        coords = coords.clone().detach().requires_grad_(True)
        # Re-run forward pass with coords requiring grad
        predictions = self.model(coords, flow_conditions) 
        
        # Unpack predictions (1D tensors for element-wise operations)
        u = predictions[:, 0]
        v = predictions[:, 1]
        w = predictions[:, 2]
        p = predictions[:, 3]
        
        # Unpack flow conditions
        viscosity = flow_conditions[:, 3]
        
        # --- First Derivatives (Gradients) ---
        
        def compute_first_derivatives(scalar: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
            # Compute gradient of scalar w.r.t coords
            grad = torch.autograd.grad(
                outputs=scalar, 
                inputs=coords, 
                grad_outputs=torch.ones_like(scalar),
                create_graph=True, 
                retain_graph=True
            )[0]
            # grad has shape [batch_size, 3] -> return dx, dy, dz derivatives
            return grad[:, 0], grad[:, 1], grad[:, 2]
        
        u_x, u_y, u_z = compute_first_derivatives(u)
        v_x, v_y, v_z = compute_first_derivatives(v)
        w_x, w_y, w_z = compute_first_derivatives(w)
        p_x, p_y, p_z = compute_first_derivatives(p)

        # Divergence (Continuity Equation)
        divergence = u_x + v_y + w_z
        
        # Convective terms
        u_conv = u * u_x + v * u_y + w * u_z
        v_conv = u * v_x + v * v_y + w * v_z
        w_conv = u * w_x + v * w_y + w * w_z
        
        # --- Second Derivatives (Laplacian) ---
        
        def compute_laplacian(grad_x: torch.Tensor, grad_y: torch.Tensor, grad_z: torch.Tensor) -> torch.Tensor:
            # Compute d/dx(grad_x) + d/dy(grad_y) + d/dz(grad_z)
            laplacian = torch.autograd.grad(grad_x.sum(), coords, create_graph=True, retain_graph=True)[0][:, 0] + \
                        torch.autograd.grad(grad_y.sum(), coords, create_graph=True, retain_graph=True)[0][:, 1] + \
                        torch.autograd.grad(grad_z.sum(), coords, create_graph=True, retain_graph=True)[0][:, 2]
            return laplacian

        laplacian_u = compute_laplacian(u_x, u_y, u_z)
        laplacian_v = compute_laplacian(v_x, v_y, v_z)
        laplacian_w = compute_laplacian(w_x, w_y, w_z)
        
        # Navier-Stokes momentum equations (density $\rho=1$)
        momentum_x = u_conv + p_x - viscosity * laplacian_u
        momentum_y = v_conv + p_y - viscosity * laplacian_v
        momentum_z = w_conv + p_z - viscosity * laplacian_w
        
        # Boundary conditions (sdf is of shape [batch_size, 1])
        boundary_mask = torch.abs(sdf.squeeze()) < 0.05
        velocity = predictions[:, :3]
        boundary_velocity_loss = torch.mean(velocity[boundary_mask]**2) if boundary_mask.any() else torch.tensor(0.0, device=self.device)
        
        freestream_velocity = flow_conditions[:, :3]
        farfield_mask = sdf.squeeze() > 1.0
        farfield_velocity_loss = torch.mean((velocity[farfield_mask] - freestream_velocity[farfield_mask])**2) if farfield_mask.any() else torch.tensor(0.0, device=self.device)
        
        # Loss dictionary
        losses = {
            'continuity': torch.mean(divergence**2),
            'momentum_x': torch.mean(momentum_x**2),
            'momentum_y': torch.mean(momentum_y**2),
            'momentum_z': torch.mean(momentum_z**2),
            'boundary_velocity': boundary_velocity_loss,
            'farfield_velocity': farfield_velocity_loss
        }
        
        return losses
    

    def predict_flow_field(self, geometry_data: Dict[str, Any], 
                         flow_conditions: Dict[str, float],
                         resolution: int = 50) -> Dict[str, Any]:
        """
        Predict flow field using trained PINN model
        """
        self.model.eval()
        
        # Create domain
        bounds = geometry_data["bounds"]
        domain = self.create_flow_domain(bounds, resolution)
        grid_points = torch.tensor(domain["grid_points"], dtype=torch.float32, device=self.device)
        
        # --- FIX STARTS HERE ---
        # 1. Prepare Trimesh Object for SDF Calculation
        vertices_np = np.array(geometry_data["vertices"], dtype=np.float32)
        faces_np = np.array(geometry_data.get("faces", []), dtype=np.int32)
        
        # Create trimesh object (Handles both vertices and faces)
        mesh = trimesh.Trimesh(vertices=vertices_np, faces=faces_np)
        
        # 2. Call SDF function with the correct (new) signature
        # We pass the mesh object, grid_points, and grid_shape
        sdf = self._compute_signed_distance_field(
            mesh, 
            grid_points, 
            domain["grid_shape"]
        )
        
        # Prepare flow conditions tensor
        flow_vel = flow_conditions.get("velocity", 1.0)
        flow_dir = flow_conditions.get("direction", [1.0, 0.0, 0.0])
        viscosity = flow_conditions.get("viscosity", 0.01)
        
        # Normalize direction
        flow_dir = np.array(flow_dir, dtype=np.float32) # Ensure NumPy array is float32
        flow_dir = flow_dir / np.linalg.norm(flow_dir)
        freestream_velocity = flow_vel * flow_dir
        
        # Create flow conditions tensor (repeated for each grid point)
        flow_conds_tensor = torch.tensor(
            [freestream_velocity[0], freestream_velocity[1], freestream_velocity[2], viscosity],
            dtype=torch.float32, # FIX: Explicitly set dtype
            device=self.device
        ).unsqueeze(0).repeat(len(grid_points), 1)
        
        # Predict in batches to avoid memory issues
        batch_size = 8192
        all_predictions = []
        
        with torch.no_grad():
            for i in range(0, len(grid_points), batch_size):
                batch_points = grid_points[i:i+batch_size]
                batch_conds = flow_conds_tensor[i:i+batch_size]
                
                batch_pred = self.model(batch_points, batch_conds)
                all_predictions.append(batch_pred.cpu())
        
        predictions = torch.cat(all_predictions, dim=0)
        velocity_field = predictions[:, :3].numpy()
        pressure_field = predictions[:, 3].numpy()
        
        # Reshape to grid
        grid_shape = domain["grid_shape"]
        velocity_field = velocity_field.reshape(grid_shape[0], grid_shape[1], grid_shape[2], 3)
        pressure_field = pressure_field.reshape(grid_shape)
        
        # Generate streamlines
        streamlines = self._generate_streamlines_pinn(velocity_field, domain, sdf)
        
        # Sample for visualization
        sample_stride = max(1, resolution // 20)
        # Create a mask for sampling points
        x_indices = np.arange(grid_shape[0])
        y_indices = np.arange(grid_shape[1])
        z_indices = np.arange(grid_shape[2])
        
        # Use np.ix_ to create the 3D grid of indices
        sampled_x, sampled_y, sampled_z = np.ix_(
            x_indices % sample_stride == 0,
            y_indices % sample_stride == 0,
            z_indices % sample_stride == 0
        )
        
        # The mask is implicitly applied by slicing/indexing
        grid_points_reshaped = grid_points.cpu().numpy().reshape(grid_shape[0], grid_shape[1], grid_shape[2], 3)
        sampled_points = grid_points_reshaped[sampled_x, sampled_y, sampled_z].reshape(-1, 3)
        sampled_velocity = velocity_field[sampled_x, sampled_y, sampled_z].reshape(-1, 3)
        
        return {
            "velocity_field": {
                "points": sampled_points.tolist(),
                "vectors": sampled_velocity.tolist(),
                "magnitude": np.linalg.norm(sampled_velocity, axis=1).tolist()
            },
            "pressure_field": pressure_field.flatten().tolist(),
            "streamlines": streamlines,
            "domain": domain,
            "sdf": sdf.cpu().numpy().flatten().tolist()
        }
    
    def create_flow_domain(self, bounds: List[List[float]], resolution: int) -> Dict[str, Any]:
        """Create 3D flow domain around the geometry"""
        padding = 0.3
        domain_bounds = [
            [bounds[0][0] - padding, bounds[1][0] + padding],
            [bounds[0][1] - padding, bounds[1][1] + padding], 
            [bounds[0][2] - padding, bounds[1][2] + padding]
        ]
        
        # Use float32 explicitly for NumPy arrays
        x = np.linspace(domain_bounds[0][0], domain_bounds[0][1], resolution, dtype=np.float32)
        y = np.linspace(domain_bounds[1][0], domain_bounds[1][1], resolution, dtype=np.float32)
        z = np.linspace(domain_bounds[2][0], domain_bounds[2][1], resolution, dtype=np.float32)
        
        X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
        grid_points = np.stack([X.flatten(), Y.flatten(), Z.flatten()], axis=1)
        
        return {
            "grid_points": grid_points.tolist(),
            "grid_shape": [resolution, resolution, resolution],
            "domain_bounds": domain_bounds,
            "coordinates": {"x": x.tolist(), "y": y.tolist(), "z": z.tolist()}
        }
    
    def _compute_signed_distance_field(self, mesh: trimesh.Trimesh, 
                                     grid_points: torch.Tensor, grid_shape: List[int]) -> torch.Tensor:
        """Compute signed distance field for boundary conditions using trimesh."""
        
        # 1. Convert grid points to NumPy for trimesh calculation
        points_np = grid_points.cpu().numpy()
        
        # 2. Use trimesh to calculate signed distance
        try:
            # Create a proximity query object from the mesh
            proximity = trimesh.proximity.ProximityQuery(mesh)
            
            # Compute distance and closest points
            # SDF is positive outside, negative inside
            signed_distance = proximity.signed_distance(points_np)
            
            # Convert back to PyTorch tensor and move to device
            sdf = torch.tensor(signed_distance, dtype=torch.float32, device=self.device)
            
        except Exception as e:
            # Fallback to the original simplified (but less accurate) calculation if trimesh fails
            print(f"Trimesh SDF calculation failed: {e}. Falling back to simplified centroid-based SDF.")
            
            sdf = torch.ones(len(grid_points), dtype=torch.float32, device=self.device) * 10.0
            
            # Simplified Centroid-based SDF fallback (as in your previous code)
            centroid = torch.tensor(mesh.centroid, dtype=torch.float32, device=self.device)
            vertices = torch.tensor(mesh.vertices, dtype=torch.float32, device=self.device)
            
            for i, point in enumerate(grid_points):
                distances = torch.norm(vertices - point, dim=1)
                min_dist = torch.min(distances)
                
                if torch.norm(point - centroid) < torch.mean(torch.norm(vertices - centroid, dim=1)):
                    sdf[i] = -min_dist
                else:
                    sdf[i] = min_dist
        
        return sdf.reshape(grid_shape)
    
    def _generate_streamlines_pinn(self, velocity_field: np.ndarray, domain: Dict[str, Any],
                                 sdf: torch.Tensor, num_streamlines: int = 30) -> List[List[List[float]]]:
        """Generate streamlines from PINN velocity field"""
        streamlines = []
        
        # Create seed points upstream of the geometry
        x_min = domain["domain_bounds"][0][0]
        # Use float32 explicitly for NumPy arrays
        y_coords = np.linspace(domain["domain_bounds"][1][0], domain["domain_bounds"][1][1], 8, dtype=np.float32)
        z_coords = np.linspace(domain["domain_bounds"][2][0], domain["domain_bounds"][2][1], 4, dtype=np.float32)
        
        seed_points = []
        for y in y_coords:
            for z in z_coords:
                seed_points.append([x_min, y, z])
        
        for seed in seed_points[:num_streamlines]:
            streamline = self._trace_streamline_pinn(seed, velocity_field, domain, sdf, max_steps=80)
            if len(streamline) > 3:
                streamlines.append(streamline)
        
        return streamlines
    
    def _trace_streamline_pinn(self, start_point: List[float], velocity_field: np.ndarray,
                             domain: Dict[str, Any], sdf: torch.Tensor, max_steps: int = 80) -> List[List[float]]:
        """Trace streamline using RK4 integration on PINN velocity field"""
        streamline = [start_point]
        point = np.array(start_point, dtype=np.float32) # Ensure starting point is float32
        step_size = 0.03
        
        for step in range(max_steps):
            vel = self._interpolate_velocity_pinn(point, velocity_field, domain)
            
            if np.linalg.norm(vel) < 0.005:
                break
            
            # RK4 integration
            k1 = vel
            k2 = self._interpolate_velocity_pinn(point + 0.5 * step_size * k1, velocity_field, domain)
            k3 = self._interpolate_velocity_pinn(point + 0.5 * step_size * k2, velocity_field, domain) 
            k4 = self._interpolate_velocity_pinn(point + step_size * k3, velocity_field, domain)
            
            point = point + (step_size / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
            
            # Check boundaries and collision with geometry
            if (self._is_outside_domain(point, domain) or 
                self._interpolate_sdf_pinn(point, sdf, domain) < -0.02):
                break
            
            streamline.append(point.tolist())
        
        return streamline
    
    def _interpolate_velocity_pinn(self, point: np.ndarray, velocity_field: np.ndarray,
                                 domain: Dict[str, Any]) -> np.ndarray:
        """Interpolate velocity from PINN grid using nearest neighbor"""
        coords = domain["coordinates"]
        grid_shape = velocity_field.shape[:3]
        
        # Find nearest grid indices
        i = np.clip(np.searchsorted(coords["x"], point[0], side='right') - 1, 0, grid_shape[0]-1)
        j = np.clip(np.searchsorted(coords["y"], point[1], side='right') - 1, 0, grid_shape[1]-1)
        k = np.clip(np.searchsorted(coords["z"], point[2], side='right') - 1, 0, grid_shape[2]-1)
        
        return velocity_field[i, j, k]
    
    def _interpolate_sdf_pinn(self, point: np.ndarray, sdf: torch.Tensor, domain: Dict[str, Any]) -> float:
        """Interpolate SDF at point using nearest neighbor"""
        coords = domain["coordinates"]
        grid_shape = sdf.shape
        
        i = np.clip(np.searchsorted(coords["x"], point[0], side='right') - 1, 0, grid_shape[0]-1)
        j = np.clip(np.searchsorted(coords["y"], point[1], side='right') - 1, 0, grid_shape[1]-1)
        k = np.clip(np.searchsorted(coords["z"], point[2], side='right') - 1, 0, grid_shape[2]-1)
        
        return sdf[i, j, k].item()
    
    def _is_outside_domain(self, point: np.ndarray, domain: Dict[str, Any]) -> bool:
        """Check if point is outside domain"""
        bounds = domain["domain_bounds"]
        return (point[0] < bounds[0][0] or point[0] > bounds[0][1] or
                point[1] < bounds[1][0] or point[1] > bounds[1][1] or
                point[2] < bounds[2][0] or point[2] > bounds[2][1])


