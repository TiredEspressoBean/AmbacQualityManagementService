"""
3D Model Processing Service

Converts supported 3D formats to optimized GLB for web viewing.

Supported formats:
    - CAD: STEP (.step, .stp) - tessellated via cascadio/OpenCASCADE
    - Mesh: STL, OBJ, PLY - loaded via trimesh
    - glTF: GLB, glTF - already in target format

Processing pipeline:
    1. Detect format type (CAD vs mesh vs glTF)
    2. Load/convert to triangulated mesh
    3. Optimize (decimate if face count exceeds target)
    4. Export to GLB

Usage:
    from Tracker.services.model_processor import ModelProcessor, ProcessingConfig

    processor = ModelProcessor(ProcessingConfig(target_faces=100_000))
    result = processor.process('/path/to/model.step')

    if result.success:
        print(f"Saved to {result.output_path}")
        print(f"Faces: {result.face_count}, Size: {result.final_size} bytes")
    else:
        print(f"Error: {result.error}")
"""
import logging
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Optional dependency: trimesh (with fast-simplification for decimation)
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    TRIMESH_AVAILABLE = False
    logger.warning("trimesh not installed - mesh optimization disabled")

# Optional dependency: cascadio (for STEP file conversion)
try:
    import cascadio
    CASCADIO_AVAILABLE = True
except ImportError:
    CASCADIO_AVAILABLE = False
    logger.warning("cascadio not installed - STEP conversion disabled")


class FormatType(Enum):
    """Classification of 3D file formats by processing requirements."""
    CAD = "cad"      # Needs tessellation (STEP, IGES, BREP)
    MESH = "mesh"    # Already triangulated (STL, OBJ, PLY)
    GLTF = "gltf"    # Target format (GLB, glTF)
    UNKNOWN = "unknown"


# Format registry: extension -> format type
FORMAT_REGISTRY = {
    # CAD formats (need tessellation)
    '.step': FormatType.CAD,
    '.stp': FormatType.CAD,
    # Note: IGES support requires pythonocc-core, not currently included
    # '.iges': FormatType.CAD,
    # '.igs': FormatType.CAD,

    # Mesh formats (already triangulated)
    '.stl': FormatType.MESH,
    '.obj': FormatType.MESH,
    '.ply': FormatType.MESH,

    # glTF formats (target format)
    '.glb': FormatType.GLTF,
    '.gltf': FormatType.GLTF,
}

# List of all accepted file extensions
ACCEPTED_EXTENSIONS = list(FORMAT_REGISTRY.keys())


@dataclass
class ProcessingConfig:
    """Configuration for 3D model processing."""

    # Mesh optimization
    target_faces: int = 100_000
    """Maximum number of triangles in output mesh. Larger meshes will be decimated."""

    min_faces: int = 5_000
    """Minimum faces to preserve. Prevents over-simplification of small meshes."""

    # CAD tessellation (for STEP files)
    linear_deflection: float = 0.1
    """Maximum distance deviation from true CAD surface (in model units)."""

    angular_deflection: float = 0.5
    """Maximum angular deviation in degrees for curved surfaces."""


@dataclass
class ProcessingResult:
    """Result of 3D model processing operation."""

    success: bool
    """Whether processing completed successfully."""

    output_path: Optional[str] = None
    """Path to the output GLB file (only set on success)."""

    face_count: int = 0
    """Number of triangles in the processed mesh."""

    vertex_count: int = 0
    """Number of vertices in the processed mesh."""

    original_size: int = 0
    """Original file size in bytes."""

    final_size: int = 0
    """Final GLB file size in bytes."""

    original_format: str = ""
    """Original file format (extension without dot)."""

    error: Optional[str] = None
    """Error message if processing failed."""

    @property
    def compression_ratio(self) -> float:
        """Calculate size reduction ratio (0.0 to 1.0)."""
        if self.original_size > 0 and self.final_size > 0:
            return 1 - (self.final_size / self.original_size)
        return 0.0

    @property
    def size_reduction_percent(self) -> float:
        """Size reduction as percentage."""
        return self.compression_ratio * 100


class ModelProcessor:
    """
    Unified 3D model processor.

    Converts any supported format to optimized GLB suitable for web viewing.
    """

    def __init__(self, config: Optional[ProcessingConfig] = None):
        """
        Initialize processor with configuration.

        Args:
            config: Processing configuration. Uses defaults if not provided.
        """
        self.config = config or ProcessingConfig()

    def detect_format(self, file_path: str) -> FormatType:
        """
        Detect format type from file extension.

        Args:
            file_path: Path to the 3D model file.

        Returns:
            FormatType enum value.
        """
        ext = Path(file_path).suffix.lower()
        return FORMAT_REGISTRY.get(ext, FormatType.UNKNOWN)

    def is_supported(self, file_path: str) -> bool:
        """Check if file format is supported."""
        return self.detect_format(file_path) != FormatType.UNKNOWN

    def process(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> ProcessingResult:
        """
        Process a 3D model file to optimized GLB.

        Args:
            input_path: Path to input file.
            output_path: Optional output path. Defaults to input path with .glb extension.

        Returns:
            ProcessingResult with success status and metrics.
        """
        input_path = Path(input_path)

        if not input_path.exists():
            return ProcessingResult(
                success=False,
                error=f"File not found: {input_path}"
            )

        original_size = input_path.stat().st_size
        original_format = input_path.suffix.lower().lstrip('.')
        format_type = self.detect_format(str(input_path))

        if format_type == FormatType.UNKNOWN:
            return ProcessingResult(
                success=False,
                original_size=original_size,
                original_format=original_format,
                error=f"Unsupported format: {input_path.suffix}. Supported: {', '.join(ACCEPTED_EXTENSIONS)}"
            )

        # Check required dependencies
        if not TRIMESH_AVAILABLE:
            return ProcessingResult(
                success=False,
                original_size=original_size,
                original_format=original_format,
                error="trimesh library not installed. Run: pip install trimesh[easy] fast-simplification"
            )

        if format_type == FormatType.CAD and not CASCADIO_AVAILABLE:
            return ProcessingResult(
                success=False,
                original_size=original_size,
                original_format=original_format,
                error="cascadio library not installed. Run: pip install cascadio"
            )

        # Determine output path
        if output_path is None:
            output_path = input_path.with_suffix('.glb')
        output_path = Path(output_path)

        try:
            # Step 1: Load/convert to mesh
            if format_type == FormatType.CAD:
                mesh = self._convert_cad_to_mesh(str(input_path))
            else:
                mesh = trimesh.load(str(input_path))

            if mesh is None:
                return ProcessingResult(
                    success=False,
                    original_size=original_size,
                    original_format=original_format,
                    error="Failed to load 3D model"
                )

            # Get original face count (before optimization)
            original_faces = self._count_faces(mesh)

            # Step 2: Optimize mesh (decimate if needed)
            mesh = self._optimize_mesh(mesh)

            # Get final metrics
            face_count, vertex_count = self._get_metrics(mesh)

            # Step 3: Export to GLB
            mesh.export(str(output_path), file_type='glb')
            final_size = output_path.stat().st_size

            logger.info(
                f"Processed {input_path.name}: {original_format}→glb, "
                f"{original_faces:,}→{face_count:,} faces, "
                f"{original_size:,}→{final_size:,} bytes "
                f"({100 - (final_size / original_size * 100):.1f}% smaller)"
            )

            return ProcessingResult(
                success=True,
                output_path=str(output_path),
                face_count=face_count,
                vertex_count=vertex_count,
                original_size=original_size,
                final_size=final_size,
                original_format=original_format,
            )

        except Exception as e:
            logger.exception(f"Processing failed for {input_path}")
            return ProcessingResult(
                success=False,
                original_size=original_size,
                original_format=original_format,
                error=str(e)
            )

    def _convert_cad_to_mesh(self, file_path: str):
        """
        Convert CAD file (STEP) to triangulated mesh using cascadio.

        Args:
            file_path: Path to STEP file.

        Returns:
            trimesh.Trimesh or trimesh.Scene object.

        Raises:
            RuntimeError: If cascadio is not available.
            ValueError: If file format is not supported by cascadio.
        """
        ext = Path(file_path).suffix.lower()

        if ext not in ['.step', '.stp']:
            raise ValueError(f"cascadio only supports STEP files, got {ext}")

        # Create temporary file for GLB output
        with tempfile.NamedTemporaryFile(suffix='.glb', delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Convert STEP to GLB using cascadio
            cascadio.step_to_glb(
                file_path,
                tmp_path,
                self.config.linear_deflection,
                self.config.angular_deflection
            )

            # Load the resulting GLB with trimesh
            return trimesh.load(tmp_path)

        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)

    def _optimize_mesh(self, mesh):
        """
        Decimate mesh to target face count if needed.

        Args:
            mesh: trimesh.Trimesh or trimesh.Scene object.

        Returns:
            Optimized mesh object.
        """
        face_count = self._count_faces(mesh)

        # Skip if already within target
        if face_count <= self.config.target_faces:
            logger.debug(f"Mesh has {face_count:,} faces, no decimation needed")
            return mesh

        logger.info(
            f"Decimating mesh from {face_count:,} to ~{self.config.target_faces:,} faces"
        )

        # Handle Scene (multiple meshes/geometries)
        if isinstance(mesh, trimesh.Scene):
            return self._optimize_scene(mesh, face_count)

        # Single mesh - straightforward decimation
        return mesh.simplify_quadric_decimation(
            face_count=self.config.target_faces
        )

    def _optimize_scene(self, scene: 'trimesh.Scene', total_faces: int):
        """
        Optimize a scene with multiple geometries.

        Distributes the target face count proportionally across geometries.
        """
        ratio = self.config.target_faces / total_faces

        for name, geom in scene.geometry.items():
            if not hasattr(geom, 'faces') or len(geom.faces) < 100:
                continue  # Skip non-mesh or tiny geometries

            # Calculate target for this geometry (proportional)
            geom_faces = len(geom.faces)
            target = max(
                int(geom_faces * ratio),
                self.config.min_faces // max(len(scene.geometry), 1)
            )

            # Only decimate if it would reduce faces
            if target < geom_faces:
                scene.geometry[name] = geom.simplify_quadric_decimation(
                    face_count=target
                )

        return scene

    def _count_faces(self, mesh) -> int:
        """Count total faces in mesh or scene."""
        if isinstance(mesh, trimesh.Scene):
            return sum(
                len(g.faces) for g in mesh.geometry.values()
                if hasattr(g, 'faces')
            )
        return len(mesh.faces) if hasattr(mesh, 'faces') else 0

    def _get_metrics(self, mesh) -> tuple[int, int]:
        """Get face and vertex counts from mesh or scene."""
        if isinstance(mesh, trimesh.Scene):
            faces = sum(
                len(g.faces) for g in mesh.geometry.values()
                if hasattr(g, 'faces')
            )
            verts = sum(
                len(g.vertices) for g in mesh.geometry.values()
                if hasattr(g, 'vertices')
            )
            return faces, verts

        faces = len(mesh.faces) if hasattr(mesh, 'faces') else 0
        verts = len(mesh.vertices) if hasattr(mesh, 'vertices') else 0
        return faces, verts


# =============================================================================
# Convenience function for simple usage
# =============================================================================

def process_model(
    input_path: str,
    output_path: str = None,
    **config_kwargs
) -> ProcessingResult:
    """
    Process a 3D model to optimized GLB.

    Convenience function that creates a ModelProcessor with the given config.

    Args:
        input_path: Path to input 3D model file.
        output_path: Optional output path (defaults to input with .glb extension).
        **config_kwargs: Arguments passed to ProcessingConfig.

    Returns:
        ProcessingResult with success status and metrics.

    Example:
        result = process_model("assembly.step", target_faces=50_000)
        if result.success:
            print(f"Saved to {result.output_path}")
    """
    config = ProcessingConfig(**config_kwargs)
    processor = ModelProcessor(config)
    return processor.process(input_path, output_path)
