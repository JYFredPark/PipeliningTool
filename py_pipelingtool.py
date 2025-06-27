import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import json
import math
from datetime import datetime

class Block:
    """Hardware block with automatic channel management"""
    
    def __init__(self, canvas, x, y, width=150, height=80, name="Module", number=None):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
        self.number = number
        self.connections = []
        self.id = None
        self.text_id = None
        self.resize_handle_id = None
        self.selected = False
        self.draw()
    
    def draw(self):
        """Draw the block on the canvas"""
        # Delete existing elements
        if self.id:
            self.canvas.delete(self.id)
        if self.text_id:
            self.canvas.delete(self.text_id)
        if self.resize_handle_id:
            self.canvas.delete(self.resize_handle_id)
        
        # Draw block rectangle
        color = "#4CAF50" if self.selected else "#2196F3"
        outline_color = "#FFA726" if self.selected else "#1976D2"
        
        self.id = self.canvas.create_rectangle(
            self.x, self.y, self.x + self.width, self.y + self.height,
            fill=color, outline=outline_color, width=2, tags="block"
        )
        
        # Draw text
        if self.number is not None:
            display_text = f"#{self.number}: {self.name}"
        else:
            display_text = self.name
            
        self.text_id = self.canvas.create_text(
            self.x + self.width/2, self.y + self.height/2,
            text=display_text, fill="white", font=("Arial", 12, "bold"), tags="block"
        )
        
        # Draw resize handle for selected blocks
        if self.selected:
            handle_size = 10
            handle_x = self.x + self.width - handle_size
            handle_y = self.y + self.height - handle_size
            self.resize_handle_id = self.canvas.create_rectangle(
                handle_x, handle_y, handle_x + handle_size, handle_y + handle_size,
                fill="#FF5722", outline="#D32F2F", width=1, tags="resize_handle"
            )
    
    def contains_point(self, x, y):
        """Check if point (x, y) is inside this block"""
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)
    
    def get_connection_point(self, other_block, connection_index=0, total_connections=1):
        """Get the point where connections should attach to this block"""
        # Determine which side of the block to use
        if other_block.x < self.x:  # Other block is to the left
            x = self.x
            y = self.y + self.height / 2
        elif other_block.x > self.x + self.width:  # Other block is to the right
            x = self.x + self.width
            y = self.y + self.height / 2
        elif other_block.y < self.y:  # Other block is above
            x = self.x + self.width / 2
            y = self.y
        else:  # Other block is below
            x = self.x + self.width / 2
            y = self.y + self.height
        
        # Offset for multiple connections
        if total_connections > 1:
            if other_block.x < self.x or other_block.x > self.x + self.width:
                # Horizontal connections - offset vertically
                offset_range = min(self.height * 0.6, total_connections * 10)
                step = offset_range / (total_connections - 1) if total_connections > 1 else 0
                offset = -offset_range/2 + connection_index * step
                y += offset
            else:
                # Vertical connections - offset horizontally
                offset_range = min(self.width * 0.6, total_connections * 10)
                step = offset_range / (total_connections - 1) if total_connections > 1 else 0
                offset = -offset_range/2 + connection_index * step
                x += offset
        
        return x, y
    
    def is_resize_handle(self, x, y):
        """Check if point is over the resize handle"""
        handle_size = 10
        handle_x = self.x + self.width - handle_size
        handle_y = self.y + self.height - handle_size
        return (handle_x <= x <= handle_x + handle_size and 
                handle_y <= y <= handle_y + handle_size)
    
    def move(self, dx, dy):
        """Move the block by the given offset"""
        self.x += dx
        self.y += dy
        self.draw()
    
    def resize(self, new_width, new_height):
        """Resize the block to new dimensions"""
        self.width = max(50, new_width)
        self.height = max(30, new_height)
        self.draw()
    
    def get_next_available_src_channel(self):
        """Get the next available source channel number for this block"""
        used_channels = set()
        for conn in self.connections:
            if hasattr(conn, 'source_block') and conn.source_block == self:
                used_channels.add(conn.src_ch_num)
        
        # Find the lowest available channel number starting from 0
        channel_num = 0
        while channel_num in used_channels:
            channel_num += 1
        return channel_num
    
    def get_next_available_dst_channel(self):
        """Get the next available destination channel number for this block"""
        used_channels = set()
        for conn in self.connections:
            if hasattr(conn, 'target_block') and conn.target_block == self:
                used_channels.add(conn.dst_ch_num)
        
        # Find the lowest available channel number starting from 0
        channel_num = 0
        while channel_num in used_channels:
            channel_num += 1
        return channel_num
    
    def can_add_connection(self):
        """Check if this block can accept more connections (max 15)"""
        return len(self.connections) < 15

class FIFOConnection:
    """FIFO connection between two blocks with automatic channel assignment"""
    
    def __init__(self, canvas, source_block, target_block, name="FIFO", depth=16, width=32, src_ch_num=None, dst_ch_num=None):
        self.canvas = canvas
        self.source_block = source_block
        self.target_block = target_block
        self.name = name
        self.depth = depth
        self.width = width
        
        # Auto-assign channel numbers if not specified
        if src_ch_num is None:
            if hasattr(source_block, 'get_next_available_src_channel'):
                self.src_ch_num = source_block.get_next_available_src_channel()
            else:
                print(f"ERROR: source_block {source_block.name} missing get_next_available_src_channel method")
                self.src_ch_num = 0
        else:
            self.src_ch_num = src_ch_num
            
        if dst_ch_num is None:
            if hasattr(target_block, 'get_next_available_dst_channel'):
                self.dst_ch_num = target_block.get_next_available_dst_channel()
            else:
                print(f"ERROR: target_block {target_block.name} missing get_next_available_dst_channel method")
                self.dst_ch_num = 0
        else:
            self.dst_ch_num = dst_ch_num
        
        self.line_id = None
        self.arrow_id = None
        self.text_id = None
        self.selected = False
        self.curve_points = []  # Store curve points for collision detection
        
        # Add this connection to both blocks
        source_block.connections.append(self)
        target_block.connections.append(self)
        self.draw()
    
    def draw(self):
        """Draw the FIFO connection on the canvas"""
        # Delete existing elements
        if self.line_id:
            self.canvas.delete(self.line_id)
        if self.arrow_id:
            self.canvas.delete(self.arrow_id)
        if self.text_id:
            self.canvas.delete(self.text_id)
        
        # Count connections between these blocks for positioning
        connections_between = []
        for conn in self.source_block.connections:
            if ((conn.source_block == self.source_block and conn.target_block == self.target_block) or
                (conn.source_block == self.target_block and conn.target_block == self.source_block)):
                connections_between.append(conn)
        
        total_connections = len(connections_between)
        connection_index = connections_between.index(self) if self in connections_between else 0
        
        # Get connection points with offset for multiple connections
        start_x, start_y = self.source_block.get_connection_point(self.target_block, connection_index, total_connections)
        end_x, end_y = self.target_block.get_connection_point(self.source_block, connection_index, total_connections)
        
        # Connection color
        color = "#FF5722" if self.selected else "#333"
        line_width = 3 if self.selected else 2
        
        # Draw connection line (straight or curved based on multiple connections)
        if total_connections > 1 and connection_index > 0:
            # Create smooth curved path for multiple connections
            mid_x = (start_x + end_x) / 2
            mid_y = (start_y + end_y) / 2
            
            # Calculate curve offset
            curve_offset = 30 + (connection_index * 15)
            
            # Determine curve direction based on block positions
            dx = end_x - start_x
            dy = end_y - start_y
            
            if abs(dx) > abs(dy):  # More horizontal connection
                curve_x = mid_x
                curve_y = mid_y + (curve_offset if connection_index % 2 == 1 else -curve_offset)
            else:  # More vertical connection
                curve_x = mid_x + (curve_offset if connection_index % 2 == 1 else -curve_offset)
                curve_y = mid_y
            
            # Create smooth curve using quadratic Bezier
            points = []
            for i in range(21):  # 21 points for smooth curve
                t = i / 20.0
                # Quadratic Bezier formula: P = (1-t)²P₀ + 2(1-t)tP₁ + t²P₂
                x = (1-t)**2 * start_x + 2*(1-t)*t * curve_x + t**2 * end_x
                y = (1-t)**2 * start_y + 2*(1-t)*t * curve_y + t**2 * end_y
                points.extend([x, y])
            
            self.line_id = self.canvas.create_line(points, fill=color, width=line_width, smooth=True, tags="connection")
            
            # Store curve points for better collision detection
            self.curve_points = points
            
        else:
            # Draw straight line for single connections
            self.line_id = self.canvas.create_line(start_x, start_y, end_x, end_y, fill=color, width=line_width, tags="connection")
            self.curve_points = [start_x, start_y, end_x, end_y]
        
        # Draw arrowhead
        arrow_color = "#FF5722" if self.selected else "#666"
        dx = end_x - start_x
        dy = end_y - start_y
        length = math.sqrt(dx*dx + dy*dy)
        
        if length > 0:
            # Normalize direction vector
            dx /= length
            dy /= length
            
            # Arrow position (slightly before the end point)
            arrow_x = end_x - dx * 12
            arrow_y = end_y - dy * 12
            
            # Arrow points
            arrow_size = 10
            perp_x = -dy * arrow_size
            perp_y = dx * arrow_size
            
            self.arrow_id = self.canvas.create_polygon(
                end_x, end_y,
                arrow_x + perp_x/2, arrow_y + perp_y/2,
                arrow_x - perp_x/2, arrow_y - perp_y/2,
                fill=arrow_color, outline=arrow_color, tags="connection"
            )
        
        # Draw connection label
        label_x = (start_x + end_x) / 2
        label_y = (start_y + end_y) / 2
        
        # Offset label to avoid overlapping the line
        if total_connections > 1 and connection_index > 0:
            # For curved connections, place label near the curve
            label_offset = 20 + (connection_index * 8)
            if abs(dx) > abs(dy):  # More horizontal
                label_y += (label_offset if connection_index % 2 == 1 else -label_offset)
            else:  # More vertical
                label_x += (label_offset if connection_index % 2 == 1 else -label_offset)
        else:
            # For straight connections, offset label above/below the line
            if abs(end_x - start_x) > abs(end_y - start_y):  # More horizontal
                label_y -= 15
            else:  # More vertical
                label_x += 15
        
        text_color = "#FF5722" if self.selected else "#000"
        self.text_id = self.canvas.create_text(
            label_x, label_y, text=self.name, 
            fill=text_color, font=("Arial", 9, "bold"), tags="connection"
        )
    
    def contains_point(self, x, y, tolerance=8):
        """Check if point is near this connection line with improved precision"""
        if not hasattr(self, 'curve_points') or not self.curve_points:
            return False
        
        points = self.curve_points
        min_distance = float('inf')
        
        # For straight lines (2 points)
        if len(points) == 4:
            x1, y1, x2, y2 = points
            distance = self._point_to_line_distance(x, y, x1, y1, x2, y2)
            return distance <= tolerance
        
        # For curved lines (multiple segments)
        for i in range(0, len(points) - 2, 2):
            x1, y1 = points[i], points[i + 1]
            x2, y2 = points[i + 2], points[i + 3]
            
            distance = self._point_to_line_distance(x, y, x1, y1, x2, y2)
            min_distance = min(min_distance, distance)
            
            if min_distance <= tolerance:
                return True
        
        return False
    
    def _point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """Calculate shortest distance from point to line segment"""
        # Vector from start to end of line
        A = px - x1
        B = py - y1
        C = x2 - x1
        D = y2 - y1
        
        dot = A * C + B * D
        len_sq = C * C + D * D
        
        if len_sq == 0:
            # Line is actually a point
            return math.sqrt(A * A + B * B)
        
        param = dot / len_sq
        
        if param < 0:
            # Point is before line start
            xx, yy = x1, y1
        elif param > 1:
            # Point is after line end
            xx, yy = x2, y2
        else:
            # Point projects onto line
            xx = x1 + param * C
            yy = y1 + param * D
        
        dx = px - xx
        dy = py - yy
        return math.sqrt(dx * dx + dy * dy)
    
    def get_connection_info(self):
        """Get descriptive info about this connection for selection"""
        return f"{self.name} ({self.source_block.name} → {self.target_block.name}) [CH{self.src_ch_num}→CH{self.dst_ch_num}]"

class HardwareDesignGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Hardware Design Tool - Block Diagram Editor")
        self.root.geometry("1200x800")
        
        # Initialize variables
        self.blocks = []
        self.connections = []
        self.selected_block = None
        self.selected_connection = None
        self.dragging = False
        self.resizing = False
        self.connecting = False
        self.connect_start_block = None
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.debug_mode = False
        self.temp_line_id = None
        
        self.create_widgets()
        self.bind_events()
        
        # Initial status
        self.status_var.set("Ready - Auto channel assignment | Manual block numbering | Edit connections in Connection Info | JSON export/import")
    
    def create_widgets(self):
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New", command=self.new_design)
        file_menu.add_separator()
        file_menu.add_command(label="Save Design (JSON)", command=self.save_json)
        file_menu.add_command(label="Load Design (JSON)", command=self.load_json)
        file_menu.add_separator()
        file_menu.add_command(label="Export Connections (JSON)", command=self.export_connections_json)
        file_menu.add_command(label="Import Connections (JSON)", command=self.import_connections_json)
        file_menu.add_separator()
        file_menu.add_command(label="Export FIFO Format", command=self.export_fifo_format)
        file_menu.add_command(label="Import FIFO Format", command=self.import_fifo_format)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Properties", command=self.edit_properties)
        edit_menu.add_command(label="Delete Selected", command=self.delete_selected)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Block Info", command=self.show_block_info)
        view_menu.add_command(label="Connection Info", command=self.show_connection_info)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help Guide", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Toolbar
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        # Create buttons with consistent spacing
        ttk.Button(toolbar, text="Add Block", command=self.add_block).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Connect mode button with visual feedback
        self.connect_button = ttk.Button(toolbar, text="Connect Mode", command=self.toggle_connect_mode)
        self.connect_button.pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Quick resize buttons
        ttk.Label(toolbar, text="Size:").pack(side=tk.LEFT, padx=(10, 2))
        ttk.Button(toolbar, text="S", command=lambda: self.quick_resize(100, 60), width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="M", command=lambda: self.quick_resize(150, 80), width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="L", command=lambda: self.quick_resize(200, 100), width=3).pack(side=tk.LEFT, padx=1)
        ttk.Button(toolbar, text="XL", command=lambda: self.quick_resize(250, 120), width=3).pack(side=tk.LEFT, padx=1)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        ttk.Button(toolbar, text="Properties", command=self.edit_properties).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Block Info", command=self.show_block_info).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Connection Info", command=self.show_connection_info).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=5)
        
        # Debug toggle button
        self.debug_button = ttk.Button(toolbar, text="Debug", command=self.toggle_debug_mode)
        self.debug_button.pack(side=tk.LEFT, padx=2)
        
        # Main canvas with scrollbars
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg="white", scrollregion=(0, 0, 2000, 2000))
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X, padx=5)
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Status bar
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar()
        status_label = ttk.Label(status_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=2)
    
    def bind_events(self):
        # Canvas events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<Button-3>", self.on_canvas_right_click)
        self.canvas.bind("<Double-Button-1>", self.on_canvas_double_click)
        self.canvas.bind("<Motion>", self.on_canvas_motion)
        
        # Keyboard events
        self.root.bind("<Key>", self.on_key_press)
        self.root.focus_set()  # Enable keyboard events
        
        # Keyboard shortcuts
        self.root.bind("<Control-n>", lambda e: self.add_block())
        self.root.bind("<Control-s>", lambda e: self.save_json())
        self.root.bind("<Control-o>", lambda e: self.load_json())
        self.root.bind("<Control-c>", lambda e: self.toggle_connect_mode())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<F2>", lambda e: self.edit_properties())
        self.root.bind("<Escape>", lambda e: self.cancel_operations())
    
    def add_block(self):
        name = simpledialog.askstring("Block Name", "Enter block name:", initialvalue="Module")
        if name:
            # Place new blocks at reasonable locations
            x, y = 100, 100
            # Offset new blocks if there are existing ones
            if self.blocks:
                max_x = max(block.x + block.width for block in self.blocks)
                x = max_x + 50
                if x > 800:  # Wrap to next row if too far right
                    x = 100
                    y = max(block.y + block.height for block in self.blocks) + 50
            
            # No auto-numbering - let user set number manually
            block = Block(self.canvas, x, y, name=name, number=None)
            self.blocks.append(block)
            self.status_var.set(f"Added block: {name} at ({x}, {y}) - Use Properties to set number")
    
    def toggle_connect_mode(self):
        self.connecting = not self.connecting
        if self.connecting:
            self.connect_button.configure(text="Exit Connect", style="Accent.TButton")
            self.status_var.set("Connect Mode: Click and drag from source block to target block")
        else:
            self.connect_button.configure(text="Connect Mode")
            self.cancel_operations()
            self.status_var.set("Connect mode disabled")
    
    def quick_resize(self, width, height):
        if self.selected_block:
            self.selected_block.resize(width, height)
            # Redraw connections that might be affected
            for conn in self.connections:
                if conn.source_block == self.selected_block or conn.target_block == self.selected_block:
                    conn.draw()
            self.status_var.set(f"Resized {self.selected_block.name} to {width}x{height}")
        else:
            messagebox.showinfo("Info", "Please select a block first")
    
    def on_canvas_click(self, event):
        # Convert screen coordinates to canvas coordinates
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.debug_mode:
            print(f"Canvas click at ({x}, {y})")
        
        # Clear previous selections
        self.clear_selections()
        
        # Check for block clicks (reverse order to prioritize top blocks)
        for block in reversed(self.blocks):
            if block.contains_point(x, y):
                if self.connecting:
                    # Connect mode logic
                    if not self.connect_start_block:
                        # First click - select source block
                        self.connect_start_block = block
                        self.status_var.set(f"Source: {block.name} - Now drag to target block")
                        return
                    else:
                        # Second click - create connection
                        if block != self.connect_start_block:
                            self.create_connection_between_blocks(self.connect_start_block, block)
                        self.connect_start_block = None
                        return
                else:
                    # Regular selection mode
                    self.selected_block = block
                    block.selected = True
                    block.draw()
                    
                    # Check for resize handle
                    if block.is_resize_handle(x, y):
                        self.resizing = True
                        self.status_var.set(f"Resizing {block.name} - drag to resize")
                    else:
                        self.dragging = True
                        self.drag_start_x = x - block.x
                        self.drag_start_y = y - block.y
                    
                    # Show connection count in status
                    conn_count = len(block.connections)
                    self.status_var.set(f"Selected: {block.name} ({conn_count}/15 connections) - Auto channel assignment enabled")
                    return
        
        # Check for connection clicks
        nearby_connections = []
        for connection in self.connections:
            if connection.contains_point(x, y):
                nearby_connections.append(connection)
        
        if nearby_connections:
            if len(nearby_connections) == 1:
                # Only one connection, select it
                self.selected_connection = nearby_connections[0]
                self.selected_connection.selected = True
                self.selected_connection.draw()
                self.status_var.set(f"Selected connection: {self.selected_connection.get_connection_info()}")
            else:
                # Multiple connections, select the first one but indicate multiple
                self.selected_connection = nearby_connections[0]
                self.selected_connection.selected = True
                self.selected_connection.draw()
                self.status_var.set(f"Selected: {self.selected_connection.get_connection_info()} (+{len(nearby_connections)-1} more) - Double-click to choose")
            return
        
        # No selection
        if self.connecting:
            self.connect_start_block = None
            self.status_var.set("Connect Mode: Click on a source block")
        else:
            self.status_var.set("Ready - Auto channel assignment | Manual block numbering | Edit connections in Connection Info | JSON export/import")
    
    def on_canvas_drag(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.connecting and self.connect_start_block:
            # Draw temporary line while connecting
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
            
            start_x, start_y = self.connect_start_block.get_connection_point(self.connect_start_block)  # Dummy for center
            start_x = self.connect_start_block.x + self.connect_start_block.width / 2
            start_y = self.connect_start_block.y + self.connect_start_block.height / 2
            
            self.temp_line_id = self.canvas.create_line(start_x, start_y, x, y, 
                                                       fill="red", width=2, dash=(5, 5), tags="temp")
            return
        
        if self.dragging and self.selected_block:
            # Move the block
            new_x = x - self.drag_start_x
            new_y = y - self.drag_start_y
            
            # Keep block within bounds
            new_x = max(0, min(new_x, 1800))
            new_y = max(0, min(new_y, 1800))
            
            self.selected_block.x = new_x
            self.selected_block.y = new_y
            self.selected_block.draw()
            
            # Redraw all connections for this block
            for conn in self.connections:
                if conn.source_block == self.selected_block or conn.target_block == self.selected_block:
                    conn.draw()
        
        elif self.resizing and self.selected_block:
            # Resize the block
            new_width = x - self.selected_block.x
            new_height = y - self.selected_block.y
            self.selected_block.resize(new_width, new_height)
            
            # Redraw connections
            for conn in self.connections:
                if conn.source_block == self.selected_block or conn.target_block == self.selected_block:
                    conn.draw()
    
    def on_canvas_release(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        if self.connecting and self.connect_start_block and self.temp_line_id:
            # Check if released over a block
            for block in self.blocks:
                if block.contains_point(x, y) and block != self.connect_start_block:
                    self.create_connection_between_blocks(self.connect_start_block, block)
                    break
            
            # Clean up temporary line
            if self.temp_line_id:
                self.canvas.delete(self.temp_line_id)
                self.temp_line_id = None
            self.connect_start_block = None
        
        self.dragging = False
        self.resizing = False
    
    def on_canvas_right_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Check what was right-clicked
        clicked_block = None
        clicked_connection = None
        
        for block in reversed(self.blocks):
            if block.contains_point(x, y):
                clicked_block = block
                break
        
        if not clicked_block:
            for connection in reversed(self.connections):
                if connection.contains_point(x, y):
                    clicked_connection = connection
                    break
        
        # Create context menu
        context_menu = tk.Menu(self.root, tearoff=0)
        
        if clicked_block:
            # Block context menu
            self.selected_block = clicked_block
            self.clear_connection_selection()
            clicked_block.selected = True
            clicked_block.draw()
            
            context_menu.add_command(label=f"Block: {clicked_block.name}", state="disabled")
            context_menu.add_separator()
            context_menu.add_command(label="Properties", command=self.edit_block_properties)
            context_menu.add_separator()
            
            # Quick connect submenu
            if len(self.blocks) > 1:
                connect_menu = tk.Menu(context_menu, tearoff=0)
                context_menu.add_cascade(label="Quick Connect to →", menu=connect_menu)
                
                for target_block in self.blocks:
                    if target_block != clicked_block:
                        connect_menu.add_command(
                            label=target_block.name,
                            command=lambda t=target_block: self.create_connection_between_blocks(clicked_block, t)
                        )
                
                context_menu.add_separator()
            
            context_menu.add_command(label="Delete Block", command=lambda: self.delete_block(clicked_block))
            
        elif clicked_connection:
            # Connection context menu
            self.selected_connection = clicked_connection
            self.clear_block_selection()
            clicked_connection.selected = True
            clicked_connection.draw()
            
            context_menu.add_command(label=f"FIFO: {clicked_connection.name}", state="disabled")
            context_menu.add_separator()
            context_menu.add_command(label="Properties", command=lambda: self.edit_connection_properties_direct(clicked_connection))
            context_menu.add_command(label="Delete Connection", command=lambda: self.delete_connection(clicked_connection))
        
        else:
            # Canvas context menu
            context_menu.add_command(label="Add Block", command=self.add_block)
            context_menu.add_separator()
            context_menu.add_command(label="Block Info", command=self.show_block_info)
            context_menu.add_command(label="Connection Info", command=self.show_connection_info)
        
        # Show context menu
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def on_canvas_double_click(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Check for block double-click first
        for block in reversed(self.blocks):
            if block.contains_point(x, y):
                self.selected_block = block
                self.edit_block_properties()
                return
        
        # Check for connection double-click - find all connections near the click point
        nearby_connections = []
        for connection in self.connections:
            if connection.contains_point(x, y):
                nearby_connections.append(connection)
        
        if nearby_connections:
            if len(nearby_connections) == 1:
                # Only one connection, edit it directly
                self.selected_connection = nearby_connections[0]
                self.edit_connection_properties_direct(nearby_connections[0])
            else:
                # Multiple connections nearby, show selection dialog
                self.show_connection_selection_dialog(nearby_connections, x, y)
    
    def show_connection_selection_dialog(self, connections, x, y):
        """Show a dialog to select which connection to edit when multiple overlap"""
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Connection to Edit")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 100, self.root.winfo_rooty() + 100))
        
        ttk.Label(dialog, text="Multiple connections found at this location.", font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(dialog, text="Select which connection to edit:").pack(pady=5)
        
        # Create listbox for connection selection
        listbox_frame = ttk.Frame(dialog)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        listbox = tk.Listbox(listbox_frame, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)
        
        # Add connections to listbox
        for i, conn in enumerate(connections):
            display_text = conn.get_connection_info()
            listbox.insert(tk.END, display_text)
        
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Select first item by default
        listbox.selection_set(0)
        
        def edit_selected():
            selection = listbox.curselection()
            if selection:
                selected_conn = connections[selection[0]]
                self.selected_connection = selected_conn
                dialog.destroy()
                self.edit_connection_properties_direct(selected_conn)
            else:
                messagebox.showinfo("Info", "Please select a connection first")
        
        def highlight_connection():
            """Highlight the selected connection in the list"""
            selection = listbox.curselection()
            if selection:
                # Clear all selections first
                for conn in connections:
                    conn.selected = False
                    conn.draw()
                
                # Highlight selected connection
                selected_conn = connections[selection[0]]
                selected_conn.selected = True
                selected_conn.draw()
        
        # Bind selection change to highlight
        listbox.bind('<<ListboxSelect>>', lambda e: highlight_connection())
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Edit Selected", command=edit_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Highlight first connection
        highlight_connection()
        
        # Focus on listbox
        listbox.focus()
        
        def on_dialog_close():
            # Clear highlighting when dialog closes
            for conn in connections:
                conn.selected = False
                conn.draw()
            dialog.destroy()
        
        dialog.protocol("WM_DELETE_WINDOW", on_dialog_close)
    
    def on_canvas_motion(self, event):
        x = self.canvas.canvasx(event.x)
        y = self.canvas.canvasy(event.y)
        
        # Update cursor based on what's under the mouse
        cursor = "arrow"
        
        if self.connecting:
            cursor = "crosshair"
        else:
            for block in self.blocks:
                if block.contains_point(x, y):
                    if block.is_resize_handle(x, y):
                        cursor = "sizing"
                    else:
                        cursor = "hand2"
                    break
        
        self.canvas.configure(cursor=cursor)
    
    def on_key_press(self, event):
        if self.debug_mode:
            print(f"Key pressed: {event.keysym}")
    
    def cancel_operations(self):
        """Cancel any ongoing operations"""
        self.connecting = False
        self.dragging = False
        self.resizing = False
        self.connect_start_block = None
        
        if self.temp_line_id:
            self.canvas.delete(self.temp_line_id)
            self.temp_line_id = None
        
        self.connect_button.configure(text="Connect Mode")
        self.canvas.configure(cursor="arrow")
    
    def clear_selections(self):
        self.clear_block_selection()
        self.clear_connection_selection()
    
    def clear_block_selection(self):
        if self.selected_block:
            self.selected_block.selected = False
            self.selected_block.draw()
            self.selected_block = None
    
    def clear_connection_selection(self):
        if self.selected_connection:
            self.selected_connection.selected = False
            self.selected_connection.draw()
            self.selected_connection = None
    
    def create_connection_between_blocks(self, source_block, target_block):
        """Helper method to create connection between two blocks with auto-assigned channel numbers"""
        if (source_block != target_block and 
            source_block.can_add_connection() and 
            target_block.can_add_connection()):
            
            # Count existing connections between these blocks
            existing_connections = sum(1 for conn in self.connections 
                                     if ((conn.source_block == source_block and 
                                          conn.target_block == target_block) or
                                         (conn.source_block == target_block and 
                                          conn.target_block == source_block)))
            
            # Create unique FIFO name
            if existing_connections > 0:
                fifo_name = f"FIFO_{existing_connections + 1}"
            else:
                fifo_name = "FIFO"
            
            # Create connection with automatic channel assignment
            conn = FIFOConnection(self.canvas, source_block, target_block, name=fifo_name)
            self.connections.append(conn)
            
            # Redraw all connections between these blocks to update positioning
            for connection in self.connections:
                if ((connection.source_block == source_block and 
                     connection.target_block == target_block) or
                    (connection.source_block == target_block and 
                     connection.target_block == source_block)):
                    connection.draw()
            
            if existing_connections > 0:
                self.status_var.set(f"Added {fifo_name} between {source_block.name} and {target_block.name} (CH{conn.src_ch_num}→CH{conn.dst_ch_num})")
            else:
                self.status_var.set(f"Connected {source_block.name} to {target_block.name} (CH{conn.src_ch_num}→CH{conn.dst_ch_num})")
            
            return True
        else:
            if source_block == target_block:
                self.status_var.set("Cannot connect block to itself")
            else:
                self.status_var.set("Cannot connect: maximum 15 connections per block reached")
            return False
    
    def edit_properties(self):
        """Edit properties of the selected item"""
        if self.selected_block:
            self.edit_block_properties()
        elif self.selected_connection:
            self.edit_connection_properties_direct(self.selected_connection)
        else:
            messagebox.showinfo("Info", "Please select a block or connection first")
    
    def edit_block_properties(self):
        """Edit properties of the selected block"""
        if not self.selected_block:
            messagebox.showinfo("Info", "Please select a block first")
            return
        
        block = self.selected_block
        
        # Create properties dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Block Properties - {block.name}")
        dialog.geometry("350x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Name field
        ttk.Label(dialog, text="Block Name:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        name_var = tk.StringVar(value=block.name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=20)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # Number field
        ttk.Label(dialog, text="Block Number:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        number_var = tk.StringVar(value=str(block.number) if block.number is not None else "")
        number_entry = ttk.Entry(dialog, textvariable=number_var, width=20)
        number_entry.grid(row=1, column=1, padx=10, pady=5)
        ttk.Label(dialog, text="(Leave empty for no number)", font=("Arial", 8)).grid(row=1, column=2, sticky="w", padx=5)
        
        # Width field
        ttk.Label(dialog, text="Width:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        width_var = tk.StringVar(value=str(int(block.width)))
        width_entry = ttk.Entry(dialog, textvariable=width_var, width=20)
        width_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Height field
        ttk.Label(dialog, text="Height:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        height_var = tk.StringVar(value=str(int(block.height)))
        height_entry = ttk.Entry(dialog, textvariable=height_var, width=20)
        height_entry.grid(row=3, column=1, padx=10, pady=5)
        
        def apply_changes():
            try:
                # Check if block still exists and is selected
                if not hasattr(self, 'selected_block') or not self.selected_block or self.selected_block != block:
                    messagebox.showerror("Error", "Block is no longer selected")
                    dialog.destroy()
                    return
                
                # Update name
                new_name = name_var.get().strip()
                if not new_name:
                    messagebox.showerror("Error", "Block name cannot be empty")
                    return
                
                # Update number
                number_text = number_var.get().strip()
                if number_text:
                    try:
                        new_number = int(number_text)
                        if new_number <= 0:
                            messagebox.showerror("Error", "Block number must be positive")
                            return
                    except ValueError:
                        messagebox.showerror("Error", "Block number must be a valid integer")
                        return
                else:
                    new_number = None
                
                # Update dimensions
                new_width = int(width_var.get())
                new_height = int(height_var.get())
                
                if new_width <= 0 or new_height <= 0:
                    messagebox.showerror("Error", "Width and height must be positive")
                    return
                
                # Apply changes to the block object directly
                block.name = new_name
                block.number = new_number
                block.resize(new_width, new_height)
                
                # Redraw block and its connections
                block.draw()
                for conn in self.connections:
                    if conn.source_block == block or conn.target_block == block:
                        conn.draw()
                
                # Update status
                number_text = f"#{new_number}" if new_number is not None else "no number"
                self.status_var.set(f"Updated block: {new_name} ({number_text})")
                
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
            except Exception as e:
                messagebox.showerror("Error", f"Unexpected error: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="Apply", command=apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Focus on name entry
        name_entry.focus()
        name_entry.select_range(0, tk.END)
    
    def delete_selected(self):
        """Delete the currently selected item"""
        if self.selected_block:
            self.delete_block(self.selected_block)
        elif self.selected_connection:
            self.delete_connection(self.selected_connection)
        else:
            messagebox.showinfo("Info", "Please select a block or connection to delete")
    
    def delete_block(self, block):
        """Delete a block and all its connections"""
        if messagebox.askyesno("Confirm Delete", f"Delete block '{block.name}' and all its connections?"):
            # Remove all connections involving this block
            connections_to_remove = [conn for conn in self.connections 
                                   if conn.source_block == block or conn.target_block == block]
            
            for conn in connections_to_remove:
                self.delete_connection(conn, confirm=False)
            
            # Remove block from canvas and list
            self.canvas.delete(block.id)
            self.canvas.delete(block.text_id)
            if block.resize_handle_id:
                self.canvas.delete(block.resize_handle_id)
            
            self.blocks.remove(block)
            
            if self.selected_block == block:
                self.selected_block = None
            
            self.status_var.set(f"Deleted block: {block.name}")
    
    def delete_connection(self, connection, confirm=True):
        """Delete a connection"""
        if confirm and not messagebox.askyesno("Confirm Delete", f"Delete connection '{connection.name}'?"):
            return
        
        # Remove from canvas
        if connection.line_id:
            self.canvas.delete(connection.line_id)
        if connection.arrow_id:
            self.canvas.delete(connection.arrow_id)
        if connection.text_id:
            self.canvas.delete(connection.text_id)
        
        # Remove from block connections
        if connection in connection.source_block.connections:
            connection.source_block.connections.remove(connection)
        if connection in connection.target_block.connections:
            connection.target_block.connections.remove(connection)
        
        # Remove from main connections list
        if connection in self.connections:
            self.connections.remove(connection)
        
        if self.selected_connection == connection:
            self.selected_connection = None
        
        # Redraw remaining connections between the same blocks to update positioning
        for conn in self.connections:
            if ((conn.source_block == connection.source_block and 
                 conn.target_block == connection.target_block) or
                (conn.source_block == connection.target_block and 
                 conn.target_block == connection.source_block)):
                conn.draw()
        
        if confirm:
            self.status_var.set(f"Deleted connection: {connection.name}")
    
    def show_block_info(self):
        """Show information about all blocks"""
        if not self.blocks:
            messagebox.showinfo("Block Info", "No blocks in design")
            return
        
        # Create info window
        info_window = tk.Toplevel(self.root)
        info_window.title("Block Information")
        info_window.geometry("700x500")
        info_window.transient(self.root)
        
        # Create treeview for block data
        columns = ("Number", "Name", "X", "Y", "Width", "Height", "Connections")
        tree = ttk.Treeview(info_window, columns=columns, show="headings", height=15)
        
        # Configure columns
        tree.heading("Number", text="Number")
        tree.heading("Name", text="Name")
        tree.heading("X", text="X")
        tree.heading("Y", text="Y")
        tree.heading("Width", text="Width")
        tree.heading("Height", text="Height")
        tree.heading("Connections", text="Connections")
        
        tree.column("Number", width=80)
        tree.column("Name", width=150)
        tree.column("X", width=60)
        tree.column("Y", width=60)
        tree.column("Width", width=80)
        tree.column("Height", width=80)
        tree.column("Connections", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        scrollbar.pack(side="right", fill="y", pady=10)
        
        # Add data for each block
        for i, block in enumerate(self.blocks):
            connection_count = len(block.connections)
            display_number = str(block.number) if block.number is not None else "-"
            tree.insert("", "end", values=(
                display_number,
                block.name,
                str(int(block.x)),
                str(int(block.y)),
                str(int(block.width)),
                str(int(block.height)),
                f"{connection_count}/15"
            ))
        
        # Button frame
        button_frame = ttk.Frame(info_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        def renumber_blocks():
            """Renumber all blocks sequentially"""
            if messagebox.askyesno("Renumber Blocks", "Renumber all blocks sequentially (1, 2, 3...)?"):
                for i, block in enumerate(self.blocks):
                    block.number = i + 1
                    block.draw()
                
                # Refresh the display
                info_window.destroy()
                self.show_block_info()
                self.status_var.set(f"Renumbered {len(self.blocks)} blocks")
        
        def edit_selected_block():
            """Edit the selected block in the tree"""
            selection = tree.selection()
            if selection:
                item = tree.item(selection[0])
                block_name = item['values'][1]  # Name is in column 1
                
                # Find the block by name
                for block in self.blocks:
                    if block.name == block_name:
                        self.selected_block = block
                        self.edit_block_properties()
                        return
                        
                messagebox.showerror("Error", "Block not found")
            else:
                messagebox.showinfo("Info", "Please select a block from the list first")
        
        ttk.Button(button_frame, text="Renumber All Blocks", command=renumber_blocks).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Edit Selected Block", command=edit_selected_block).pack(side=tk.LEFT, padx=5)
        
        # Close button
        ttk.Button(info_window, text="Close", command=info_window.destroy).pack(pady=10)
    
    def show_connection_info(self):
        """Show information about all connections"""
        if not self.connections:
            messagebox.showinfo("Connection Info", "No connections in design")
            return
        
        # Create info window
        info_window = tk.Toplevel(self.root)
        info_window.title("Connection Information")
        info_window.geometry("900x600")
        info_window.transient(self.root)
        
        # Statistics
        stats_frame = ttk.Frame(info_window)
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        total_connections = len(self.connections)
        # Group connections by block pairs for statistics
        connection_groups = {}
        for conn in self.connections:
            pair_key = f"{conn.source_block.name} ↔ {conn.target_block.name}"
            if pair_key not in connection_groups:
                connection_groups[pair_key] = []
            connection_groups[pair_key].append(conn)
        
        total_pairs = len(connection_groups)
        ttk.Label(stats_frame, text=f"Total connections: {total_connections} | Block pairs: {total_pairs} | Channel numbers assigned automatically").pack()
        
        # Create main frame for treeview and scrollbar
        main_frame = ttk.Frame(info_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for connection data
        columns = ("FIFO Name", "Source", "Src CH", "Destination", "Dst CH", "Depth", "Width")
        tree = ttk.Treeview(main_frame, columns=columns, show="headings", height=20)
        
        # Configure columns
        for col in columns:
            tree.heading(col, text=col)
        
        tree.column("FIFO Name", width=120)
        tree.column("Source", width=100)
        tree.column("Src CH", width=60)
        tree.column("Destination", width=100)
        tree.column("Dst CH", width=60)
        tree.column("Depth", width=60)
        tree.column("Width", width=60)
        
        # Add data grouped by block pairs
        connection_list = []  # Keep track of connections for editing
        for block_pair in sorted(connection_groups.keys()):
            connections = connection_groups[block_pair]
            
            # Add block pair header
            tree.insert("", "end", values=(f"=== {block_pair} ===", "", "", "", "", "", ""))
            
            # Add connections for this block pair
            for conn in connections:
                item_id = tree.insert("", "end", values=(
                    conn.name,
                    conn.source_block.name,
                    str(conn.src_ch_num),
                    conn.target_block.name,
                    str(conn.dst_ch_num),
                    str(conn.depth),
                    str(conn.width)
                ))
                connection_list.append((item_id, conn))  # Store mapping
            
            # Add blank line for separation
            tree.insert("", "end", values=("", "", "", "", "", "", ""))
        
        def on_double_click(event):
            """Handle double-click to edit connection"""
            selection = tree.selection()
            if selection:
                item_id = selection[0]
                # Find the connection for this item
                for stored_id, conn in connection_list:
                    if stored_id == item_id:
                        self.edit_connection_properties_direct(conn)
                        # Refresh the display
                        info_window.destroy()
                        self.show_connection_info()
                        break
        
        def edit_selected_connection():
            """Edit the selected connection in the tree"""
            selection = tree.selection()
            if selection:
                item_id = selection[0]
                # Find the connection for this item
                for stored_id, conn in connection_list:
                    if stored_id == item_id:
                        self.edit_connection_properties_direct(conn)
                        # Refresh the display
                        info_window.destroy()
                        self.show_connection_info()
                        return
                messagebox.showinfo("Info", "Selected item is not a connection")
            else:
                messagebox.showinfo("Info", "Please select a connection from the list first")
        
        # Bind double-click event
        tree.bind("<Double-1>", on_double_click)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Button frame for actions
        button_frame = ttk.Frame(info_window)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Edit Selected Connection", command=edit_selected_connection).pack(side=tk.LEFT, padx=5)
        
        def reassign_all_channels():
            """Reassign all channel numbers automatically"""
            if not self.connections:
                messagebox.showinfo("Info", "No connections to reassign")
                return
            
            result = messagebox.askyesno("Reassign Channels", 
                "This will reassign all channel numbers automatically.\n"
                "Current channel assignments will be lost.\n\n"
                "Continue?")
            
            if result:
                # Clear all connections temporarily to reset channel assignments
                for conn in self.connections:
                    # Remove from block connection lists
                    if conn in conn.source_block.connections:
                        conn.source_block.connections.remove(conn)
                    if conn in conn.target_block.connections:
                        conn.target_block.connections.remove(conn)
                
                # Reassign channel numbers and add back to blocks
                for conn in self.connections:
                    conn.src_ch_num = conn.source_block.get_next_available_src_channel()
                    conn.dst_ch_num = conn.target_block.get_next_available_dst_channel()
                    
                    # Add back to block connection lists
                    conn.source_block.connections.append(conn)
                    conn.target_block.connections.append(conn)
                    
                    # Redraw connection
                    conn.draw()
                
                # Refresh the display
                info_window.destroy()
                self.show_connection_info()
                self.status_var.set(f"Reassigned channel numbers for {len(self.connections)} connections")
        
        ttk.Button(button_frame, text="Reassign All Channels", command=reassign_all_channels).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Export Connections to JSON", command=self.export_connections_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Import Connections from JSON", command=self.import_connections_json).pack(side=tk.LEFT, padx=5)
        
        # Close button
        ttk.Button(info_window, text="Close", command=info_window.destroy).pack(pady=10)
    
    def edit_connection_properties_direct(self, connection):
        """Edit properties of a specific connection"""
        # Create properties dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Edit Connection Properties - {connection.name}")
        dialog.geometry("400x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.geometry("+%d+%d" % (self.root.winfo_rootx() + 50, self.root.winfo_rooty() + 50))
        
        # Configure grid weights
        dialog.grid_columnconfigure(1, weight=1)
        
        # Connection info header
        ttk.Label(dialog, text="Connection Information", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))
        ttk.Label(dialog, text=f"From: {connection.source_block.name} → To: {connection.target_block.name}").grid(row=1, column=0, columnspan=2, pady=(0, 15))
        
        # FIFO name field
        ttk.Label(dialog, text="FIFO Name:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        name_var = tk.StringVar(value=connection.name)
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=25)
        name_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        
        # Depth field
        ttk.Label(dialog, text="Queue Depth:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
        depth_var = tk.StringVar(value=str(connection.depth))
        depth_entry = ttk.Entry(dialog, textvariable=depth_var, width=25)
        depth_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        
        # Width field
        ttk.Label(dialog, text="Data Width:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
        width_var = tk.StringVar(value=str(connection.width))
        width_entry = ttk.Entry(dialog, textvariable=width_var, width=25)
        width_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        
        # Source channel field
        ttk.Label(dialog, text="Source Channel:").grid(row=5, column=0, sticky="w", padx=10, pady=5)
        src_ch_var = tk.StringVar(value=str(connection.src_ch_num))
        src_ch_entry = ttk.Entry(dialog, textvariable=src_ch_var, width=25)
        src_ch_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        
        # Destination channel field
        ttk.Label(dialog, text="Destination Channel:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
        dst_ch_var = tk.StringVar(value=str(connection.dst_ch_num))
        dst_ch_entry = ttk.Entry(dialog, textvariable=dst_ch_var, width=25)
        dst_ch_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")
        
        def apply_changes():
            try:
                new_name = name_var.get().strip()
                new_depth = int(depth_var.get())
                new_width = int(width_var.get())
                new_src_ch = int(src_ch_var.get())
                new_dst_ch = int(dst_ch_var.get())
                
                if not new_name:
                    messagebox.showerror("Error", "FIFO name cannot be empty")
                    return
                
                if new_depth <= 0 or new_width <= 0:
                    messagebox.showerror("Error", "Depth and width must be positive")
                    return
                
                if new_src_ch < 0 or new_dst_ch < 0:
                    messagebox.showerror("Error", "Channel numbers cannot be negative")
                    return
                
                # Apply changes
                connection.name = new_name
                connection.depth = new_depth
                connection.width = new_width
                connection.src_ch_num = new_src_ch
                connection.dst_ch_num = new_dst_ch
                
                # Redraw connection
                connection.draw()
                
                self.status_var.set(f"Updated connection: {new_name}")
                dialog.destroy()
                
            except ValueError as e:
                messagebox.showerror("Error", f"Invalid input: {str(e)}")
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Apply", command=apply_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)
        
        # Focus on name entry
        name_entry.focus()
        name_entry.select_range(0, tk.END)
    
    def export_connections_json(self):
        """Export all connections to a JSON file with compact horizontal formatting"""
        if not self.connections:
            messagebox.showinfo("Info", "No connections to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Connections to JSON"
        )
        
        if filename:
            try:
                # Create fifo_infos array with compact format
                fifo_infos = []
                for conn in self.connections:
                    conn_data = {
                        "name": conn.name,
                        "src": conn.source_block.name,
                        "src_ch_num": conn.src_ch_num,
                        "dst": conn.target_block.name,
                        "dst_ch_num": conn.dst_ch_num,
                        "qd": conn.depth,
                        "width": conn.width
                    }
                    fifo_infos.append(conn_data)
                
                connections_data = {
                    "metadata": {
                        "exported_from": "Hardware Design Tool",
                        "export_date": datetime.now().isoformat(),
                        "total_connections": len(self.connections)
                    },
                    "fifo_infos": fifo_infos
                }
                
                # Write with custom formatting
                with open(filename, 'w') as f:
                    self.write_compact_json(f, connections_data)
                
                self.status_var.set(f"Exported {len(self.connections)} connections to {filename}")
                messagebox.showinfo("Success", f"Exported {len(self.connections)} connections to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export connections:\n{str(e)}")
    
    def write_compact_json(self, file, data):
        """Write JSON with compact horizontal formatting for fifo_infos"""
        file.write("{\n")
        
        # Write metadata section normally
        if "metadata" in data:
            file.write('  "metadata": ')
            json.dump(data["metadata"], file, indent=2)
            file.write(",\n")
        
        # Write fifo_infos with compact formatting
        if "fifo_infos" in data:
            file.write('  "fifo_infos": [\n')
            fifo_infos = data["fifo_infos"]
            for i, fifo in enumerate(fifo_infos):
                file.write("    ")
                # Write each connection as a single line
                json.dump(fifo, file, separators=(',', ': '))
                if i < len(fifo_infos) - 1:
                    file.write(",")
                file.write("\n")
            file.write("  ]\n")
        
        # Write other sections normally
        for key, value in data.items():
            if key not in ["metadata", "fifo_infos"]:
                file.write(f'  "{key}": ')
                json.dump(value, file, indent=2)
                file.write("\n")
        
        file.write("}")
    
    def import_connections_json(self):
        """Import connections from a JSON file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Connections from JSON"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                # Support both new "fifo_infos" format and old "connections" format
                if "fifo_infos" in data:
                    connections_data = data["fifo_infos"]
                    format_type = "fifo_infos"
                elif "connections" in data:
                    connections_data = data["connections"]
                    format_type = "connections"
                else:
                    messagebox.showerror("Error", "Invalid JSON format: neither 'fifo_infos' nor 'connections' key found")
                    return
                
                # Create a map of existing blocks
                block_map = {block.name: block for block in self.blocks}
                
                imported_count = 0
                skipped_count = 0
                error_messages = []
                
                for conn_data in connections_data:
                    try:
                        # Handle both formats
                        if format_type == "fifo_infos":
                            source_name = conn_data["src"]
                            dest_name = conn_data["dst"]
                            fifo_name = conn_data.get("name", "FIFO")
                            queue_depth = conn_data.get("qd", 16)
                            data_width = conn_data.get("width", 32)
                            source_channel = conn_data.get("src_ch_num", 0)
                            dest_channel = conn_data.get("dst_ch_num", 0)
                        else:  # connections format
                            source_name = conn_data["source_block"]
                            dest_name = conn_data["destination_block"]
                            fifo_name = conn_data.get("fifo_name", "FIFO")
                            queue_depth = conn_data.get("queue_depth", 16)
                            data_width = conn_data.get("data_width", 32)
                            source_channel = conn_data.get("source_channel", 0)
                            dest_channel = conn_data.get("destination_channel", 0)
                        
                        if source_name not in block_map:
                            error_messages.append(f"Source block '{source_name}' not found")
                            skipped_count += 1
                            continue
                        
                        if dest_name not in block_map:
                            error_messages.append(f"Destination block '{dest_name}' not found")
                            skipped_count += 1
                            continue
                        
                        source_block = block_map[source_name]
                        dest_block = block_map[dest_name]
                        
                        # Check if blocks can accept more connections
                        if not source_block.can_add_connection():
                            error_messages.append(f"Source block '{source_name}' has reached connection limit")
                            skipped_count += 1
                            continue
                        
                        if not dest_block.can_add_connection():
                            error_messages.append(f"Destination block '{dest_name}' has reached connection limit")
                            skipped_count += 1
                            continue
                        
                        # Create the connection with preserved channel numbers
                        conn = FIFOConnection(
                            self.canvas,
                            source_block,
                            dest_block,
                            fifo_name,
                            queue_depth,
                            data_width,
                            source_channel,  # Preserve imported channel numbers
                            dest_channel     # Preserve imported channel numbers
                        )
                        self.connections.append(conn)
                        imported_count += 1
                        
                    except Exception as e:
                        error_messages.append(f"Error importing connection: {str(e)}")
                        skipped_count += 1
                
                # Show results
                result_msg = f"Import completed!\nImported: {imported_count} connections\nSkipped: {skipped_count} connections"
                
                if error_messages:
                    result_msg += f"\n\nErrors encountered:\n" + "\n".join(error_messages[:10])
                    if len(error_messages) > 10:
                        result_msg += f"\n... and {len(error_messages) - 10} more errors"
                
                if imported_count > 0:
                    messagebox.showinfo("Import Results", result_msg)
                    self.status_var.set(f"Imported {imported_count} connections from JSON")
                else:
                    messagebox.showwarning("Import Results", result_msg)
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import connections:\n{str(e)}")
    
    def new_design(self):
        """Create a new design (clear all blocks and connections)"""
        if self.blocks or self.connections:
            if not messagebox.askyesno("New Design", "This will clear the current design. Continue?"):
                return
        
        # Clear canvas
        self.canvas.delete("all")
        
        # Clear data structures
        self.blocks = []
        self.connections = []
        self.selected_block = None
        self.selected_connection = None
        
        # Reset states
        self.cancel_operations()
        
        self.status_var.set("New design created")
    
    def save_json(self):
        """Save design to JSON file with compact connection formatting"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                # Create design data structure
                design_data = {
                    "metadata": {
                        "created_by": "Hardware Design Tool",
                        "created_date": datetime.now().isoformat(),
                        "version": "1.0"
                    },
                    "blocks": [],
                    "fifo_infos": []
                }
                
                # Save blocks
                for block in self.blocks:
                    block_data = {
                        "x": block.x,
                        "y": block.y,
                        "width": block.width,
                        "height": block.height,
                        "name": block.name,
                        "number": block.number,
                    }
                    design_data["blocks"].append(block_data)
                
                # Save connections in compact format
                for conn in self.connections:
                    conn_data = {
                        "name": conn.name,
                        "src": conn.source_block.name,
                        "src_ch_num": conn.src_ch_num,
                        "dst": conn.target_block.name,
                        "dst_ch_num": conn.dst_ch_num,
                        "qd": conn.depth,
                        "width": conn.width
                    }
                    design_data["fifo_infos"].append(conn_data)
                
                # Write with custom formatting
                with open(filename, 'w') as f:
                    self.write_compact_design_json(f, design_data)
                
                self.status_var.set(f"Saved to {filename}")
                messagebox.showinfo("Success", f"Design saved to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def write_compact_design_json(self, file, data):
        """Write full design JSON with compact horizontal formatting for fifo_infos"""
        file.write("{\n")
        
        # Write metadata section
        if "metadata" in data:
            file.write('  "metadata": ')
            json.dump(data["metadata"], file, indent=2)
            file.write(",\n")
        
        # Write blocks section
        if "blocks" in data:
            file.write('  "blocks": ')
            json.dump(data["blocks"], file, indent=2)
            file.write(",\n")
        
        # Write fifo_infos with compact formatting
        if "fifo_infos" in data:
            file.write('  "fifo_infos": [\n')
            fifo_infos = data["fifo_infos"]
            for i, fifo in enumerate(fifo_infos):
                file.write("    ")
                # Write each connection as a single line
                json.dump(fifo, file, separators=(',', ': '))
                if i < len(fifo_infos) - 1:
                    file.write(",")
                file.write("\n")
            file.write("  ]\n")
        
        file.write("}")
    
    def load_json(self):
        """Load design from JSON file (supports both old and new formats)"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    design_data = json.load(f)
                
                # Clear current design
                self.new_design()
                
                if "blocks" not in design_data:
                    messagebox.showerror("Error", "Invalid JSON format")
                    return
                
                # Load blocks
                block_map = {}
                for block_data in design_data.get("blocks", []):
                    block = Block(
                        self.canvas,
                        block_data["x"],
                        block_data["y"],
                        block_data["width"],
                        block_data["height"],
                        block_data["name"],
                        block_data.get("number")  # Load number if available
                    )
                    self.blocks.append(block)
                    block_map[block.name] = block
                
                # Load connections - handle both old and new formats
                if "fifo_infos" in design_data:
                    # New format with fifo_infos
                    for conn_data in design_data["fifo_infos"]:
                        source_name = conn_data["src"]
                        target_name = conn_data["dst"]
                        if source_name in block_map and target_name in block_map:
                            source_block = block_map[source_name]
                            target_block = block_map[target_name]
                            conn = FIFOConnection(
                                self.canvas,
                                source_block,
                                target_block,
                                conn_data["name"],
                                conn_data["qd"],
                                conn_data["width"],
                                conn_data.get("src_ch_num", 0),  # Preserve saved channel numbers
                                conn_data.get("dst_ch_num", 0)   # Preserve saved channel numbers
                            )
                            self.connections.append(conn)
                
                else:
                    # Old format with connections nested in blocks
                    for block_data in design_data.get("blocks", []):
                        source_block = block_map[block_data["name"]]
                        for conn_data in block_data.get("connections", []):
                            target_name = conn_data["target"]
                            if target_name in block_map:
                                target_block = block_map[target_name]
                                conn = FIFOConnection(
                                    self.canvas,
                                    source_block,
                                    target_block,
                                    conn_data["name"],
                                    conn_data["depth"],
                                    conn_data["width"],
                                    conn_data.get("src_ch_num", 0),  # Preserve saved channel numbers
                                    conn_data.get("dst_ch_num", 0)   # Preserve saved channel numbers
                                )
                                self.connections.append(conn)
                
                self.status_var.set(f"Loaded from {filename}")
                messagebox.showinfo("Success", f"Design loaded from:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load: {str(e)}")
    
    def export_fifo_format(self):
        """Export connections in FIFO format with compact horizontal formatting"""
        if not self.connections:
            messagebox.showinfo("Info", "No connections to export")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export FIFO Format"
        )
        
        if filename:
            try:
                # Create fifo_infos array
                fifo_infos = []
                for conn in self.connections:
                    fifo_data = {
                        "name": conn.name,
                        "src": conn.source_block.name,
                        "src_ch_num": conn.src_ch_num,
                        "dst": conn.target_block.name,
                        "dst_ch_num": conn.dst_ch_num,
                        "qd": conn.depth,
                        "width": conn.width
                    }
                    fifo_infos.append(fifo_data)
                
                data = {
                    "fifo_infos": fifo_infos
                }
                
                # Write with compact formatting
                with open(filename, 'w') as f:
                    self.write_compact_json(f, data)
                
                self.status_var.set(f"Exported FIFO format to {filename}")
                messagebox.showinfo("Success", f"FIFO format exported to:\n{filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export FIFO format: {str(e)}")
    
    def import_fifo_format(self):
        """Import connections from FIFO format"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import FIFO Format"
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                
                if "fifo_infos" not in data:
                    messagebox.showerror("Error", "Invalid FIFO format: 'fifo_infos' key not found")
                    return
                
                # Clear current design and create blocks from FIFO data
                self.new_design()
                
                # Extract unique block names from connections
                block_names = set()
                for fifo_info in data["fifo_infos"]:
                    block_names.add(fifo_info["src"])
                    block_names.add(fifo_info["dst"])
                
                # Create blocks in a grid layout
                block_map = {}
                cols = math.ceil(math.sqrt(len(block_names)))
                x_offset = 50
                y_offset = 50
                
                for i, block_name in enumerate(sorted(block_names)):
                    x = x_offset + (i % cols) * 200
                    y = y_offset + (i // cols) * 150
                    
                    block = Block(self.canvas, x, y, name=block_name, number=i + 1)
                    self.blocks.append(block)
                    block_map[block_name] = block
                
                # Create connections
                for fifo_info in data["fifo_infos"]:
                    src_name = fifo_info["src"]
                    dst_name = fifo_info["dst"]
                    
                    if src_name in block_map and dst_name in block_map:
                        source_block = block_map[src_name]
                        target_block = block_map[dst_name]
                        
                        # Check connection limits
                        if not (source_block.can_add_connection() and target_block.can_add_connection()):
                            messagebox.showwarning("Warning", 
                                f"Skipping connection {fifo_info['name']}: connection limit exceeded")
                            continue
                        
                        conn = FIFOConnection(
                            self.canvas,
                            source_block,
                            target_block,
                            fifo_info["name"],
                            fifo_info["qd"],
                            fifo_info["width"],
                            fifo_info["src_ch_num"],  # Preserve imported channel numbers
                            fifo_info["dst_ch_num"]   # Preserve imported channel numbers
                        )
                        self.connections.append(conn)
                
                self.status_var.set(f"Imported FIFO format from {filename}")
                messagebox.showinfo("Success", 
                    f"FIFO format imported from:\n{filename}\n\n"
                    f"Created {len(self.blocks)} blocks and {len(self.connections)} connections")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import FIFO format: {str(e)}")
    
    def toggle_debug_mode(self):
        """Toggle debug mode on/off"""
        self.debug_mode = not self.debug_mode
        status = "enabled" if self.debug_mode else "disabled"
        self.status_var.set(f"Debug mode {status}")
    
    def show_help(self):
        """Show help guide"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Hardware Design Tool - Help Guide")
        help_window.geometry("800x700")
        help_window.transient(self.root)
        
        # Create scrollable text widget
        text_frame = ttk.Frame(help_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        help_text = """HARDWARE DESIGN TOOL - HELP GUIDE

=== CREATING BLOCKS ===
• Click "Add Block" or press Ctrl+N
• Enter a name for your hardware module
• Set block numbers manually via Properties (right-click → Properties)
• Move blocks by clicking and dragging
• Resize blocks by dragging the orange handle in bottom-right corner

=== BLOCK NUMBERING ===
• Block numbers are optional and user-defined
• Edit block number via Properties dialog (right-click → Properties)
• Leave number field empty for no number display
• Numbers help organize large designs

=== BLOCK SIZING OPTIONS ===
• Manual resize: Drag the orange handle on selected blocks
• Quick resize buttons: S (Small), M (Medium), L (Large), XL (Extra Large)
• Select a block first, then click size buttons in toolbar

=== CONNECTING BLOCKS (Multiple Ways) ===

Method 1 - Drag to Connect (Easiest):
• Click "Connect Mode" or press Ctrl+C
• Click and drag from source block to target block
• Visual feedback shows temporary connection line
• Creates connection automatically when you release
• Channel numbers assigned automatically (0, 1, 2, ...)

Method 2 - Right-Click Quick Connect (Fastest):
• Right-click on any block
• Select "Quick Connect to →" and choose target
• Or select "Connect from [BlockName]..." for step-by-step

=== AUTOMATIC CHANNEL ASSIGNMENT ===
• Source and destination channel numbers assigned automatically
• Uses lowest available channel number for each block
• Example: Block with channels 0,1,3 → next connection gets channel 2
• Preserves manual assignments when loading saved files
• "Reassign All Channels" button to reset all channel numbers

=== FIFO CONNECTION DISPLAY ===
• FIFO connections show only the FIFO name for clarity
• View all properties in "Connection Info" dialog
• Edit properties by double-clicking or right-clicking connections
• Status bar shows channel assignments when connections created

=== MULTIPLE CONNECTIONS ===
• Up to 15 connections per block supported
• Multiple FIFOs between same blocks automatically:
  - Separated visually with curves
  - Named uniquely (FIFO, FIFO_2, FIFO_3, etc.)
  - Spread along block edges to avoid overlap
  - Each gets unique channel numbers automatically

=== INFORMATION TABS ===

Block Info Tab:
• View all blocks with numbers, names, positions, sizes
• See connection counts for each block (X/15)
• Renumber all blocks sequentially
• Edit selected block properties directly

Connection Info Tab (Interactive):
• Columns: FIFO Name, Source, Src CH, Destination, Dst CH, Depth, Width
• Grouped by block pairs for better organization
• Double-click any connection to edit properties
• "Edit Selected Connection" button for property editing
• "Reassign All Channels" to reset channel numbering
• Export/Import connections to/from JSON

=== JSON CONNECTION EXPORT/IMPORT ===
• Export connections: Save all FIFO connections to JSON file
• Import connections: Load connections from JSON to existing blocks
• Preserves all connection properties including channel numbers
• Useful for sharing connection configurations
• Access via Connection Info tab or File menu

=== EDITING PROPERTIES ===
• Double-click any block or connection
• Right-click and select "Properties"
• Select item and press F2
• Connection properties: name, depth, width, channel numbers (manual override)
• Block properties: name, width, height, number (optional)

=== SELECTION AND DELETION ===
• Left-click to select blocks or connections
• Press Delete key to remove selected items
• Right-click for context menus with quick actions

=== DEBUG MODE ===
• Click "Debug" button to toggle debug output on/off
• Helpful for troubleshooting interaction issues
• Shows detailed click, drag, and selection information

=== KEYBOARD SHORTCUTS ===
• Ctrl+N: Add new block
• Ctrl+C: Toggle connect mode
• Ctrl+S: Save design
• Ctrl+O: Load design
• Delete: Remove selected item
• F2: Edit properties
• Escape: Cancel operations

=== FILE OPERATIONS ===
• Save/Load Design: Full design with blocks, connections, and numbers
• Export/Import Connections: Just connection data in JSON format
• Export/Import FIFO Format: For external tools
• All formats preserve block numbers and connection properties

=== TIPS FOR BETTER PRODUCTIVITY ===
• Use block numbers for large designs (edit via Properties)
• Use larger blocks (L or XL) for complex designs
• Export connections as JSON templates for reuse
• Connect Mode + drag is fastest for multiple connections
• Channel numbers assigned automatically - no manual setup needed
• Use "Reassign All Channels" if channel numbering gets messy
• Right-click is your friend for quick operations
• Block Info and Connection Info tabs help manage complex designs
• Double-click connections in Connection Info for quick editing
• Use Debug mode if you encounter interaction issues"""
        
        text_widget.insert(tk.END, help_text)
        text_widget.configure(state=tk.DISABLED)  # Make read-only
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Close button
        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Hardware Design Tool
Block Diagram Editor

Version 1.0

Features:
• Visual block diagram creation
• Automatic FIFO connection management
• Multiple connection types between blocks
• JSON export/import functionality
• Interactive property editing
• Automatic channel assignment

Created for hardware design workflows."""
        
        messagebox.showinfo("About Hardware Design Tool", about_text)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = HardwareDesignGUI()
    app.run()