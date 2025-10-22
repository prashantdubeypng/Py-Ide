"""
SecureExecutor - Docker-based sandboxed code execution
Runs user code in isolated containers with resource limits
"""
import docker
import tempfile
import os
import textwrap
import re
from pathlib import Path
from typing import Dict, List, Optional
from ide.utils.logger import logger


class CodeValidator:
    """Pre-execution static analysis for dangerous code patterns"""
    
    BANNED_PATTERNS = [
        r'os\.system',
        r'subprocess\.',
        r'socket\.',
        r'open\s*\(\s*["\']/',  # Absolute file paths
        r'eval\s*\(',
        r'exec\s*\(',
        r'__import__\s*\(',
        r'compile\s*\(',
        r'breakpoint\s*\(',
        r'globals\s*\(',
        r'locals\s*\(',
        r'vars\s*\(',
        r'dir\s*\(',
        r'help\s*\(',
        r'input\s*\(',  # Prevent blocking
        r'exit\s*\(',
        r'quit\s*\(',
    ]
    
    DANGEROUS_IMPORTS = [
        'os',
        'subprocess',
        'socket',
        'sys',
        'ctypes',
        'multiprocessing',
        'threading',
        '__builtin__',
        'builtins',
        'importlib',
        'pty',
        'fcntl',
        'resource',
    ]
    
    @classmethod
    def validate(cls, code: str, strict: bool = False) -> tuple[bool, Optional[str]]:
        """
        Validate code for dangerous patterns
        
        Args:
            code: Python code to validate
            strict: If True, blocks more imports
            
        Returns:
            (is_valid, error_message)
        """
        # Check banned patterns
        for pattern in cls.BANNED_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Blocked dangerous pattern: {pattern}"
        
        # Check dangerous imports (basic detection)
        if strict:
            for dangerous in cls.DANGEROUS_IMPORTS:
                if re.search(rf'\bimport\s+{dangerous}\b', code):
                    return False, f"Blocked dangerous import: {dangerous}"
                if re.search(rf'\bfrom\s+{dangerous}\s+import\b', code):
                    return False, f"Blocked dangerous import: {dangerous}"
        
        return True, None


class SecureExecutor:
    """
    Executes user code safely inside an isolated Docker container.
    
    Features:
    - Network isolation
    - Resource limits (CPU, RAM)
    - Read-only filesystem
    - Temporary workspace with auto-cleanup
    - Pre-execution validation
    - Timeout protection
    """
    
    def __init__(
        self,
        image: str = "python:3.11-slim",
        mem_limit: str = "256m",
        cpu_quota: int = 50000,  # 50% of one core
        max_output_size: int = 10000,  # Max chars in output
        enable_validation: bool = True,
        strict_validation: bool = False
    ):
        """
        Initialize SecureExecutor
        
        Args:
            image: Docker image to use
            mem_limit: Memory limit (e.g., "256m", "512m")
            cpu_quota: CPU quota in microseconds (100000 = 1 core)
            max_output_size: Maximum output size in characters
            enable_validation: Enable pre-execution code validation
            strict_validation: Use strict validation (blocks more imports)
        """
        try:
            self.client = docker.from_env()
            # Verify Docker is accessible
            self.client.ping()
            logger.info("Docker client initialized successfully")
        except docker.errors.DockerException as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise RuntimeError(
                "Docker is not available. Please ensure Docker Desktop is running."
            ) from e
        
        self.image = image
        self.mem_limit = mem_limit
        self.cpu_quota = cpu_quota
        self.max_output_size = max_output_size
        self.enable_validation = enable_validation
        self.strict_validation = strict_validation
        
        # Ensure image is available
        self._ensure_image()
    
    def _ensure_image(self):
        """Pull Docker image if not available"""
        try:
            self.client.images.get(self.image)
            logger.info(f"Docker image {self.image} is available")
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling Docker image {self.image}...")
            try:
                self.client.images.pull(self.image)
                logger.info(f"Successfully pulled {self.image}")
            except Exception as e:
                logger.error(f"Failed to pull image: {e}")
                raise RuntimeError(f"Failed to pull Docker image {self.image}") from e
    
    def _create_temp_script(self, code: str) -> tuple[str, str]:
        """
        Save code in a temporary file (sandboxed workspace)
        
        Returns:
            (script_path, tmp_dir)
        """
        tmp_dir = tempfile.mkdtemp(prefix="ide_sandbox_")
        script_path = os.path.join(tmp_dir, "main.py")
        
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(code))
        
        logger.debug(f"Created temp script at {script_path}")
        return script_path, tmp_dir
    
    def _cleanup_temp(self, tmp_dir: str):
        """Clean up temporary directory"""
        try:
            for file in Path(tmp_dir).glob("*"):
                file.unlink()
            Path(tmp_dir).rmdir()
            logger.debug(f"Cleaned up temp directory {tmp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def run_code(
        self,
        code: str,
        timeout: int = 5,
        validate: Optional[bool] = None
    ) -> Dict[str, any]:
        """
        Execute Python code inside a sandboxed Docker container
        
        Args:
            code: Python code to execute
            timeout: Execution timeout in seconds
            validate: Override default validation setting
            
        Returns:
            dict with:
                - exit_code: Exit code (0 = success)
                - output: Combined stdout/stderr
                - error: Error message if failed
                - validated: Whether code was validated
        """
        # Validation
        should_validate = validate if validate is not None else self.enable_validation
        
        if should_validate:
            is_valid, error_msg = CodeValidator.validate(code, self.strict_validation)
            if not is_valid:
                logger.warning(f"Code validation failed: {error_msg}")
                return {
                    "exit_code": 1,
                    "output": "",
                    "error": f"🚫 Security validation failed: {error_msg}",
                    "validated": True
                }
        
        # Create temporary script
        script_path, tmp_dir = self._create_temp_script(code)
        
        try:
            logger.info("Starting sandboxed code execution")
            
            # Run container with strict isolation
            container = self.client.containers.run(
                self.image,
                command=["python", "-u", "/sandbox/main.py"],  # -u for unbuffered
                network_disabled=True,  # No network access
                mem_limit=self.mem_limit,  # Memory limit
                cpu_quota=self.cpu_quota,  # CPU limit
                detach=True,
                remove=True,  # Auto-remove after execution
                volumes={tmp_dir: {"bind": "/sandbox", "mode": "ro"}},  # Read-only
                working_dir="/sandbox",
                stdin_open=False,
                tty=False,
                user="nobody",  # Run as non-root
                cap_drop=["ALL"],  # Drop all capabilities
                security_opt=["no-new-privileges"],  # Prevent privilege escalation
            )
            
            # Wait for completion with timeout
            result = container.wait(timeout=timeout)
            
            # Get logs
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            
            # Truncate output if too large
            if len(logs) > self.max_output_size:
                logs = logs[:self.max_output_size] + f"\n\n⚠️ Output truncated (limit: {self.max_output_size} chars)"
            
            exit_code = result.get("StatusCode", 1)
            
            logger.info(f"Code execution completed with exit code {exit_code}")
            
            return {
                "exit_code": exit_code,
                "output": logs,
                "error": None if exit_code == 0 else "Non-zero exit code",
                "validated": should_validate
            }
        
        except docker.errors.ContainerError as e:
            logger.error(f"Container error: {e}")
            return {
                "exit_code": 1,
                "output": "",
                "error": f"Container error: {str(e)[:200]}",
                "validated": should_validate
            }
        
        except Exception as e:
            logger.error(f"Execution error: {e}", exc_info=True)
            return {
                "exit_code": 1,
                "output": "",
                "error": f"Execution error: {str(e)[:200]}",
                "validated": should_validate
            }
        
        finally:
            # Always cleanup
            self._cleanup_temp(tmp_dir)
    
    def run_code_streaming(
        self,
        code: str,
        timeout: int = 5,
        callback=None
    ) -> Dict[str, any]:
        """
        Execute code with streaming output (for real-time logs)
        
        Args:
            code: Python code to execute
            timeout: Timeout in seconds
            callback: Function to call with each log line
            
        Returns:
            Same as run_code()
        """
        # Validation
        if self.enable_validation:
            is_valid, error_msg = CodeValidator.validate(code, self.strict_validation)
            if not is_valid:
                return {
                    "exit_code": 1,
                    "output": "",
                    "error": f"Security validation failed: {error_msg}",
                    "validated": True
                }
        
        script_path, tmp_dir = self._create_temp_script(code)
        
        try:
            container = self.client.containers.run(
                self.image,
                command=["python", "-u", "/sandbox/main.py"],
                network_disabled=True,
                mem_limit=self.mem_limit,
                cpu_quota=self.cpu_quota,
                detach=True,
                volumes={tmp_dir: {"bind": "/sandbox", "mode": "ro"}},
                working_dir="/sandbox",
                user="nobody",
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
            )
            
            # Stream logs in real-time
            output_lines = []
            for line in container.logs(stream=True, follow=True):
                decoded = line.decode("utf-8", errors="replace")
                output_lines.append(decoded)
                
                if callback:
                    callback(decoded)
                
                # Check size limit
                if sum(len(l) for l in output_lines) > self.max_output_size:
                    container.stop()
                    break
            
            # Wait for completion
            result = container.wait(timeout=timeout)
            full_output = "".join(output_lines)
            
            return {
                "exit_code": result.get("StatusCode", 1),
                "output": full_output,
                "error": None,
                "validated": True
            }
        
        except Exception as e:
            logger.error(f"Streaming execution error: {e}")
            return {
                "exit_code": 1,
                "output": "",
                "error": str(e),
                "validated": True
            }
        
        finally:
            try:
                container.remove(force=True)
            except:
                pass
            self._cleanup_temp(tmp_dir)
    
    def is_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        try:
            self.client.ping()
            return True
        except:
            return False
    
    def get_container_stats(self) -> Dict[str, any]:
        """Get executor configuration stats"""
        return {
            "image": self.image,
            "mem_limit": self.mem_limit,
            "cpu_quota": self.cpu_quota,
            "max_output_size": self.max_output_size,
            "validation_enabled": self.enable_validation,
            "strict_validation": self.strict_validation,
            "docker_available": self.is_docker_available()
        }


# Singleton instance for IDE-wide use
_executor_instance: Optional[SecureExecutor] = None


def get_executor(
    mem_limit: str = "256m",
    cpu_quota: int = 50000,
    enable_validation: bool = True
) -> SecureExecutor:
    """Get or create SecureExecutor singleton instance"""
    global _executor_instance
    
    if _executor_instance is None:
        _executor_instance = SecureExecutor(
            mem_limit=mem_limit,
            cpu_quota=cpu_quota,
            enable_validation=enable_validation
        )
    
    return _executor_instance


if __name__ == "__main__":
    # Test the executor
    executor = SecureExecutor()
    
    test_code = """
import math
print("Hello from sandbox!")
print("Math.pi =", math.pi)
print("Files in sandbox:", __file__)
"""
    
    print("Testing SecureExecutor...")
    result = executor.run_code(test_code)
    
    print(f"\nExit code: {result['exit_code']}")
    print(f"Output:\n{result['output']}")
    
    if result['error']:
        print(f"Error: {result['error']}")
