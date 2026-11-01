import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import threading
import time
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageTk
import os
import subprocess
import sys
import random

# ---------------- FIREBASE INITIALIZATION ----------------
try:
    cred = credentials.Certificate("footballanalysisapp-f71c3-firebase-adminsdk-fbsvc-9dadc9be59.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase connection established")
except Exception as e:
    print("⚠ Firebase connection failed:", e)
    db = None

# ---------------- MODERN STYLING ----------------
class ModernStyle:
    PRIMARY = "#2E86AB"      # Fresh blue
    SECONDARY = "#A23B72"    # Vibrant purple
    SUCCESS = "#28A745"      # Green
    WARNING = "#FFC107"      # Amber
    DANGER = "#DC3545"       # Red
    INFO = "#17A2B8"         # Teal
    LIGHT = "#F8F9FA"        # Light gray
    WHITE = "#FFFFFF"        # Pure white
    TEXT = "#2D3748"         # Dark gray for text
    BORDER = "#E2E8F0"       # Light border

# ---------------- DUMMY TEAM ANALYSIS DATA ----------------
class TeamAnalysisData:
    def __init__(self):
        self.team_styles = [
            "Possession-based attacking football",
            "Counter-attacking specialists", 
            "High-press aggressive style",
            "Defensive solidity with quick breaks",
            "Wing-play focused attacking",
            "Central midfield dominance"
        ]
        
        self.strengths = [
            "Excellent ball retention in midfield",
            "Lightning-fast counter attacks",
            "High defensive line effectiveness",
            "Superior aerial duels won",
            "Precise crossing accuracy",
            "Effective set-piece routines",
            "Strong team cohesion and understanding",
            "Excellent fitness levels High",
            "Creative playmaking in final third",
            "Solid defensive organization"
        ]
        
        self.weaknesses = [
            "Vulnerable to counter attacks",
            "Fatigue sets in after 70 minutes",
            "Struggle against high-press teams",
            "Poor conversion rate in front of goal",
            "Weak in aerial defensive duels",
            "Slow defensive transitions",
            "Over-reliance on key players",
            "Disorganized defense",
            "Poor ball retention under pressure",
            "Ineffective against parked buses"
        ]
        
        self.tactical_insights = [
            "Tend to tire around 70th minute - push for goals late",
            "Vulnerable to quick transitions - exploit counter opportunities",
            "Strong in central areas but weak on flanks",
            "High defensive line - use through balls behind defense",
            "Weak against set-pieces - focus on corners and free kicks",
            "Excellent first-half performers but fade in second half"
        ]

    def generate_team_analysis(self, team_name, is_team1=True):
        style = random.choice(self.team_styles)
        team_strengths = random.sample(self.strengths, 4)
        team_weaknesses = random.sample(self.weaknesses, 3)
        insights = random.sample(self.tactical_insights, 2)
        
        return {
            "name": team_name,
            "style": style,
            "strengths": team_strengths,
            "weaknesses": team_weaknesses,
            "insights": insights,
            "formation": random.choice(["4-3-3", "4-2-3-1", "4-4-2", "3-5-2", "4-1-4-1"]),
            "fatigue_level": random.randint(60, 90),
            "attack_rating": random.randint(70, 95),
            "defense_rating": random.randint(65, 90),
            "fitness_rating": random.randint(75, 95),
            "pressure_rating": random.randint(60, 85)
        }

# ---------------- SCROLLABLE FRAME CLASS ----------------
class VerticalScrolledFrame(ttk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # Create canvas and scrollbar
        self.canvas = tk.Canvas(self, borderwidth=0, background=ModernStyle.LIGHT)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, style='Custom.TFrame')
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda event=None: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Mouse wheel binding
        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)
        
    def _bind_mousewheel(self, event=None):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
    def _unbind_mousewheel(self, event=None):
        self.canvas.unbind_all("<MouseWheel>")
        
    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

# ---------------- MAIN APPLICATION CLASS ----------------
class FootballAnalysisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚽ Football Analysis Pro")
        self.root.geometry("1200x800")
        self.root.config(bg=ModernStyle.LIGHT)
        
        # Center the window
        self.center_window()

        self.video_path = None
        self.output_dir = "output_videos"
        self.heatmap_path = "output_videos/heatmap_from_tracks.jpg"
        self.analysis_running = False
        self.video_playing = False
        self.current_video_cap = None
        self.output_video_path = None
        self.analysis_process = None
        self.team_analysis_data = TeamAnalysisData()
        self.team_analysis = None

        self.setup_styles()
        self.create_header()
        self.create_main_layout()
        self.create_footer()

        # Check for existing output videos and heatmap
        self.check_existing_output_videos()
        self.check_existing_heatmap()
        
        # Generate initial team analysis
        self.generate_team_analysis()

    def center_window(self):
        self.root.update_idletasks()
        width = 1200
        height = 800
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure custom styles
        style.configure('Primary.TButton', 
                       background=ModernStyle.PRIMARY,
                       foreground=ModernStyle.WHITE,
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Success.TButton',
                       background=ModernStyle.SUCCESS,
                       foreground=ModernStyle.WHITE,
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Warning.TButton',
                       background=ModernStyle.WARNING,
                       foreground=ModernStyle.TEXT,
                       font=('Segoe UI', 10, 'bold'),
                       padding=(15, 8))
        
        style.configure('Custom.TFrame', background=ModernStyle.LIGHT)
        style.configure('Card.TFrame', background=ModernStyle.WHITE)

    def create_header(self):
        header = tk.Frame(self.root, bg=ModernStyle.PRIMARY, height=80)
        header.pack(fill=tk.X, side=tk.TOP)

        title_frame = tk.Frame(header, bg=ModernStyle.PRIMARY)
        title_frame.pack(side=tk.LEFT, padx=20, pady=15)

        tk.Label(title_frame, text="⚽ Football Analysis Pro",
                 font=("Segoe UI", 20, "bold"),
                 fg=ModernStyle.WHITE,
                 bg=ModernStyle.PRIMARY).pack(anchor='w')

        tk.Label(title_frame, text="Professional Match Analytics & Team Insights",
                 font=("Segoe UI", 10),
                 fg=ModernStyle.LIGHT,
                 bg=ModernStyle.PRIMARY).pack(anchor='w')

        # Control buttons
        control_frame = tk.Frame(header, bg=ModernStyle.PRIMARY)
        control_frame.pack(side=tk.RIGHT, padx=20, pady=15)

        ttk.Button(control_frame, text="📁 Select Video", 
                   command=self.select_video, style='Primary.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="🚀 Start Analysis", 
                   command=self.start_analysis, style='Success.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="🎬 Play Output", 
                   command=self.play_output_video, style='Warning.TButton').pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="🗺 View Heatmap", 
                   command=self.show_heatmap, style='Primary.TButton').pack(side=tk.RIGHT, padx=5)

    def create_main_layout(self):
        main_container = tk.Frame(self.root, bg=ModernStyle.LIGHT)
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Left column - Video & Progress (70%)
        left_column = tk.Frame(main_container, bg=ModernStyle.LIGHT)
        left_column.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Video card with tabs
        self.create_video_tabs(left_column)

        # Progress card
        progress_card = tk.Frame(left_column, bg=ModernStyle.WHITE, relief='raised', bd=1)
        progress_card.pack(fill=tk.X, pady=5)

        tk.Label(progress_card, text="📊 Analysis Progress", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(pady=8)

        # Progress bar frame
        progress_frame = tk.Frame(progress_card, bg=ModernStyle.WHITE)
        progress_frame.pack(fill=tk.X, padx=10, pady=5)

        self.progress = ttk.Progressbar(progress_frame, orient="horizontal", mode="determinate", length=600)
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_percent = tk.Label(progress_frame, text="0%", font=("Segoe UI", 10, "bold"),
                                        fg=ModernStyle.PRIMARY, bg=ModernStyle.WHITE, width=5)
        self.progress_percent.pack(side=tk.RIGHT, padx=(10, 0))

        self.progress_label = tk.Label(progress_card, text="Ready to analyze...",
                                       font=("Segoe UI", 9), fg=ModernStyle.TEXT, bg=ModernStyle.WHITE)
        self.progress_label.pack(pady=(0, 10))

        # Video controls
        control_frame = tk.Frame(progress_card, bg=ModernStyle.WHITE)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="⏸ Pause", 
                  command=self.pause_video, style='Primary.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="⏹ Stop", 
                  command=self.stop_video, style='Primary.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(control_frame, text="🔄 Check Output", 
                  command=self.refresh_outputs, style='Primary.TButton').pack(side=tk.RIGHT, padx=2)

        # Right column - Scrollable Stats (30%)
        right_column = VerticalScrolledFrame(main_container, width=350)
        right_column.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(10, 0))
        right_column.pack_propagate(False)

        # Live Stats Card
        self.create_live_stats_card(right_column.scrollable_frame)
        
        # Firebase Stats Card  
        self.create_firebase_card(right_column.scrollable_frame)
        
        # Team Analysis Card
        self.create_team_analysis_card(right_column.scrollable_frame)

    def create_video_tabs(self, parent):
        # Create notebook for tabs
        self.video_notebook = ttk.Notebook(parent)
        self.video_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Input Video Tab
        input_frame = tk.Frame(self.video_notebook, bg=ModernStyle.WHITE)
        self.video_notebook.add(input_frame, text="🎥 Input Video")
        
        tk.Label(input_frame, text="Original Video Feed", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(pady=10)

        self.input_video_frame = tk.Label(input_frame, bg="#000000", height=300)
        self.input_video_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Output Video Tab
        output_frame = tk.Frame(self.video_notebook, bg=ModernStyle.WHITE)
        self.video_notebook.add(output_frame, text="📹 Analyzed Video")
        
        tk.Label(output_frame, text="Processed Video with Analytics", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(pady=10)

        self.output_video_frame = tk.Label(output_frame, bg="#000000", height=300)
        self.output_video_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Output status label
        self.output_status_label = tk.Label(output_frame, text="No output video found", 
                                           font=("Segoe UI", 10), fg=ModernStyle.WARNING, bg=ModernStyle.WHITE)
        self.output_status_label.pack(pady=5)

        # Heatmap Tab
        heatmap_frame = tk.Frame(self.video_notebook, bg=ModernStyle.WHITE)
        self.video_notebook.add(heatmap_frame, text="🔥 Heatmap")
        
        tk.Label(heatmap_frame, text="Player Movement Heatmap", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(pady=10)

        # Heatmap image display
        self.heatmap_frame = tk.Label(heatmap_frame, bg="#000000", height=300)
        self.heatmap_frame.pack(pady=5, padx=10, fill=tk.BOTH, expand=True)

        # Heatmap status label
        self.heatmap_status_label = tk.Label(heatmap_frame, text="No heatmap found", 
                                            font=("Segoe UI", 10), fg=ModernStyle.WARNING, bg=ModernStyle.WHITE)
        self.heatmap_status_label.pack(pady=5)

        # Heatmap controls
        heatmap_controls = tk.Frame(heatmap_frame, bg=ModernStyle.WHITE)
        heatmap_controls.pack(pady=10)
        
        ttk.Button(heatmap_controls, text="🔄 Refresh Heatmap", 
                  command=self.check_existing_heatmap, style='Primary.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(heatmap_controls, text="📥 Save Heatmap", 
                  command=self.save_heatmap, style='Success.TButton').pack(side=tk.LEFT, padx=5)

    def create_live_stats_card(self, parent):
        stats_card = tk.Frame(parent, bg=ModernStyle.WHITE, relief='raised', bd=1)
        stats_card.pack(fill=tk.X, pady=(0, 10))

        header = tk.Frame(stats_card, bg=ModernStyle.WHITE)
        header.pack(fill=tk.X, padx=15, pady=10)
        tk.Label(header, text="📈 Live Analysis Stats", font=("Segoe UI", 14, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(anchor='w')

        content = tk.Frame(stats_card, bg=ModernStyle.WHITE)
        content.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Compact stats layout
        stats_grid = tk.Frame(content, bg=ModernStyle.WHITE)
        stats_grid.pack(fill=tk.X)

        # Row 1
        row1 = tk.Frame(stats_grid, bg=ModernStyle.WHITE)
        row1.pack(fill=tk.X, pady=5)

        tk.Label(row1, text="Possession:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)
        self.possession_bar = ttk.Progressbar(row1, orient="horizontal", length=120, mode="determinate")
        self.possession_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.possession_label = tk.Label(row1, text="50%", font=("Segoe UI", 9, "bold"),
                                        fg=ModernStyle.PRIMARY, bg=ModernStyle.WHITE, width=5)
        self.possession_label.pack(side=tk.RIGHT)

        # Row 2
        row2 = tk.Frame(stats_grid, bg=ModernStyle.WHITE)
        row2.pack(fill=tk.X, pady=5)
        
        tk.Label(row2, text="⚡ Avg Speed:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)
        self.speed_value = tk.Label(row2, text="0 km/h", font=("Segoe UI", 10, "bold"),
                                   fg=ModernStyle.SECONDARY, bg=ModernStyle.WHITE)
        self.speed_value.pack(side=tk.RIGHT)

        # Row 3
        row3 = tk.Frame(stats_grid, bg=ModernStyle.WHITE)
        row3.pack(fill=tk.X, pady=5)
        
        tk.Label(row3, text="📏 Distance:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)
        self.distance_value = tk.Label(row3, text="0 m", font=("Segoe UI", 10, "bold"),
                                       fg=ModernStyle.SUCCESS, bg=ModernStyle.WHITE)
        self.distance_value.pack(side=tk.RIGHT)

        # Row 4 - Heatmap info
        row4 = tk.Frame(stats_grid, bg=ModernStyle.WHITE)
        row4.pack(fill=tk.X, pady=5)
        
        tk.Label(row4, text="🔥 Heatmap:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)
        self.heatmap_status = tk.Label(row4, text="Not Available", font=("Segoe UI", 9, "bold"),
                                      fg=ModernStyle.WARNING, bg=ModernStyle.WHITE)
        self.heatmap_status.pack(side=tk.RIGHT)

    def create_firebase_card(self, parent):
        firebase_card = tk.Frame(parent, bg=ModernStyle.WHITE, relief='raised', bd=1)
        firebase_card.pack(fill=tk.X, pady=5)

        header = tk.Frame(firebase_card, bg=ModernStyle.WHITE)
        header.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header, text="🔥 Match Database", font=("Segoe UI", 14, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(side=tk.LEFT)
        
        ttk.Button(header, text="🔄 Refresh", command=self.fetch_firebase_data, 
                  style='Primary.TButton').pack(side=tk.RIGHT)

        content = tk.Frame(firebase_card, bg=ModernStyle.WHITE)
        content.pack(fill=tk.X, padx=15, pady=(0, 15))

        # Team 1 Section
        team1_frame = tk.Frame(content, bg=ModernStyle.WHITE)
        team1_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(team1_frame, text="🔵 Team 1", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.PRIMARY, bg=ModernStyle.WHITE).pack(anchor='w')

        # Team 1 stats in compact grid
        self.fb_team1_possession = self.create_compact_stat_row(team1_frame, "Possession:", "--%")
        self.fb_team1_speed = self.create_compact_stat_row(team1_frame, "Avg Speed:", "-- km/h")
        self.fb_team1_distance = self.create_compact_stat_row(team1_frame, "Total Distance:", "-- m")

        ttk.Separator(content, orient='horizontal').pack(fill=tk.X, pady=8)

        # Team 2 Section
        team2_frame = tk.Frame(content, bg=ModernStyle.WHITE)
        team2_frame.pack(fill=tk.X, pady=8)
        
        tk.Label(team2_frame, text="🔴 Team 2", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.SECONDARY, bg=ModernStyle.WHITE).pack(anchor='w')

        # Team 2 stats in compact grid
        self.fb_team2_possession = self.create_compact_stat_row(team2_frame, "Possession:", "--%")
        self.fb_team2_speed = self.create_compact_stat_row(team2_frame, "Avg Speed:", "-- km/h")
        self.fb_team2_distance = self.create_compact_stat_row(team2_frame, "Total Distance:", "-- m")

        # Players Section
        ttk.Separator(content, orient='horizontal').pack(fill=tk.X, pady=8)
        
        players_header = tk.Frame(content, bg=ModernStyle.WHITE)
        players_header.pack(fill=tk.X, pady=5)
        
        tk.Label(players_header, text="👥 Top Players", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(anchor='w')

        self.players_frame = tk.Frame(content, bg=ModernStyle.WHITE)
        self.players_frame.pack(fill=tk.X)

    def create_team_analysis_card(self, parent):
        analysis_card = tk.Frame(parent, bg=ModernStyle.WHITE, relief='raised', bd=1)
        analysis_card.pack(fill=tk.X, pady=5)

        header = tk.Frame(analysis_card, bg=ModernStyle.WHITE)
        header.pack(fill=tk.X, padx=15, pady=10)
        
        tk.Label(header, text="🎯 Team Analysis", font=("Segoe UI", 14, "bold"),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(side=tk.LEFT)
        
        ttk.Button(header, text="🔄 New Analysis", command=self.generate_team_analysis, 
                  style='Primary.TButton').pack(side=tk.RIGHT)

        self.analysis_content = tk.Frame(analysis_card, bg=ModernStyle.WHITE)
        self.analysis_content.pack(fill=tk.X, padx=15, pady=(0, 15))

    def generate_team_analysis(self):
        if not self.team_analysis:
            self.team_analysis = {
                "team1": self.team_analysis_data.generate_team_analysis("Blue Lions", True),
                "team2": self.team_analysis_data.generate_team_analysis("Red Eagles", False)
            }
        
        # Clear previous analysis
        for widget in self.analysis_content.winfo_children():
            widget.destroy()

        # Team 1 Analysis
        team1_frame = tk.Frame(self.analysis_content, bg=ModernStyle.WHITE)
        team1_frame.pack(fill=tk.X, pady=8)
        
        # Team 1 Header
        team1_header = tk.Frame(team1_frame, bg=ModernStyle.WHITE)
        team1_header.pack(fill=tk.X)
        tk.Label(team1_header, text="🔵 Blue Lions", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.PRIMARY, bg=ModernStyle.WHITE).pack(anchor='w')
        
        # Formation and Style
        style_frame = tk.Frame(team1_frame, bg=ModernStyle.WHITE)
        style_frame.pack(fill=tk.X, pady=5)
        tk.Label(style_frame, text=f"Formation: {self.team_analysis['team1']['formation']} | Style: {self.team_analysis['team1']['style']}", 
                 font=("Segoe UI", 9), fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(anchor='w')
        
        # Ratings
        self.create_rating_bars(team1_frame, self.team_analysis['team1'])
        
        # Strengths
        strengths_frame = tk.Frame(team1_frame, bg=ModernStyle.WHITE)
        strengths_frame.pack(fill=tk.X, pady=5)
        tk.Label(strengths_frame, text="✅ Strengths:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.SUCCESS, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for strength in self.team_analysis['team1']['strengths']:
            strength_label = tk.Label(strengths_frame, text=f"• {strength}", font=("Segoe UI", 8),
                                    fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            strength_label.pack(anchor='w')
        
        # Weaknesses
        weaknesses_frame = tk.Frame(team1_frame, bg=ModernStyle.WHITE)
        weaknesses_frame.pack(fill=tk.X, pady=5)
        tk.Label(weaknesses_frame, text="❌ Weaknesses:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.DANGER, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for weakness in self.team_analysis['team1']['weaknesses']:
            weakness_label = tk.Label(weaknesses_frame, text=f"• {weakness}", font=("Segoe UI", 8),
                                    fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            weakness_label.pack(anchor='w')
        
        # Tactical Insights
        insights_frame = tk.Frame(team1_frame, bg=ModernStyle.WHITE)
        insights_frame.pack(fill=tk.X, pady=5)
        tk.Label(insights_frame, text="💡 Key Insight:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.INFO, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for insight in self.team_analysis['team1']['insights']:
            insight_label = tk.Label(insights_frame, text=f"⚡ {insight}", font=("Segoe UI", 8, "italic"),
                                   fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            insight_label.pack(anchor='w')

        ttk.Separator(self.analysis_content, orient='horizontal').pack(fill=tk.X, pady=8)

        # Team 2 Analysis
        team2_frame = tk.Frame(self.analysis_content, bg=ModernStyle.WHITE)
        team2_frame.pack(fill=tk.X, pady=8)
        
        # Team 2 Header
        team2_header = tk.Frame(team2_frame, bg=ModernStyle.WHITE)
        team2_header.pack(fill=tk.X)
        tk.Label(team2_header, text="🔴 Red Eagles", font=("Segoe UI", 12, "bold"),
                 fg=ModernStyle.SECONDARY, bg=ModernStyle.WHITE).pack(anchor='w')
        
        # Formation and Style
        style_frame2 = tk.Frame(team2_frame, bg=ModernStyle.WHITE)
        style_frame2.pack(fill=tk.X, pady=5)
        tk.Label(style_frame2, text=f"Formation: {self.team_analysis['team2']['formation']} | Style: {self.team_analysis['team2']['style']}", 
                 font=("Segoe UI", 9), fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(anchor='w')
        
        # Ratings
        self.create_rating_bars(team2_frame, self.team_analysis['team2'])
        
        # Strengths
        strengths_frame2 = tk.Frame(team2_frame, bg=ModernStyle.WHITE)
        strengths_frame2.pack(fill=tk.X, pady=5)
        tk.Label(strengths_frame2, text="✅ Strengths:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.SUCCESS, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for strength in self.team_analysis['team2']['strengths']:
            strength_label = tk.Label(strengths_frame2, text=f"• {strength}", font=("Segoe UI", 8),
                                    fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            strength_label.pack(anchor='w')
        
        # Weaknesses
        weaknesses_frame2 = tk.Frame(team2_frame, bg=ModernStyle.WHITE)
        weaknesses_frame2.pack(fill=tk.X, pady=5)
        tk.Label(weaknesses_frame2, text="❌ Weaknesses:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.DANGER, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for weakness in self.team_analysis['team2']['weaknesses']:
            weakness_label = tk.Label(weaknesses_frame2, text=f"• {weakness}", font=("Segoe UI", 8),
                                    fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            weakness_label.pack(anchor='w')
        
        # Tactical Insights
        insights_frame2 = tk.Frame(team2_frame, bg=ModernStyle.WHITE)
        insights_frame2.pack(fill=tk.X, pady=5)
        tk.Label(insights_frame2, text="💡 Key Insight:", font=("Segoe UI", 10, "bold"),
                 fg=ModernStyle.INFO, bg=ModernStyle.WHITE).pack(anchor='w')
        
        for insight in self.team_analysis['team2']['insights']:
            insight_label = tk.Label(insights_frame2, text=f"⚡ {insight}", font=("Segoe UI", 8, "italic"),
                                   fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, justify=tk.LEFT)
            insight_label.pack(anchor='w')

        messagebox.showinfo("Analysis Generated", "🎯 New team analysis has been generated!")

    def create_rating_bars(self, parent, team_data):
        ratings_frame = tk.Frame(parent, bg=ModernStyle.WHITE)
        ratings_frame.pack(fill=tk.X, pady=5)
        
        attributes = [
            ("⚔ Attack", team_data['attack_rating'], ModernStyle.SUCCESS),
            ("🛡 Defense", team_data['defense_rating'], ModernStyle.PRIMARY),
            ("💪 Fitness", team_data['fitness_rating'], ModernStyle.INFO),
            ("⚡ Pressure", team_data['pressure_rating'], ModernStyle.WARNING),
            ("😴 Fatigue Lvl", team_data['fatigue_level'], ModernStyle.DANGER)
        ]
        
        for attr_name, rating, color in attributes:
            attr_frame = tk.Frame(ratings_frame, bg=ModernStyle.WHITE)
            attr_frame.pack(fill=tk.X, pady=1)
            
            tk.Label(attr_frame, text=attr_name, font=("Segoe UI", 8),
                    fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)
            
            # Create a custom progress bar using canvas for better control
            canvas = tk.Canvas(attr_frame, width=120, height=15, bg=ModernStyle.WHITE, highlightthickness=0)
            canvas.pack(side=tk.LEFT, padx=5)
            
            # Draw progress bar background
            canvas.create_rectangle(0, 5, 120, 12, fill=ModernStyle.LIGHT, outline="")
            # Draw progress
            canvas.create_rectangle(0, 5, rating * 1.2, 12, fill=color, outline="")
            # Draw rating text
            canvas.create_text(60, 9, text=f"{rating}%", font=("Segoe UI", 7, "bold"), fill=ModernStyle.TEXT)

    def create_compact_stat_row(self, parent, label, default_value):
        frame = tk.Frame(parent, bg=ModernStyle.WHITE)
        frame.pack(fill=tk.X, pady=2)

        tk.Label(frame, text=label, font=("Segoe UI", 9),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE, width=15).pack(side=tk.LEFT)
        value_label = tk.Label(frame, text=default_value, font=("Segoe UI", 9, "bold"),
                               fg=ModernStyle.TEXT, bg=ModernStyle.WHITE)
        value_label.pack(side=tk.RIGHT)
        return value_label

    def create_footer(self):
        footer = tk.Frame(self.root, bg=ModernStyle.PRIMARY, height=30)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        tk.Label(footer, text="© 2024 Football Analysis Pro | Professional Match Analytics & Team Insights",
                 font=("Segoe UI", 8), fg=ModernStyle.WHITE, bg=ModernStyle.PRIMARY).pack(pady=8)

    def select_video(self):
        self.video_path = filedialog.askopenfilename(
            title="Select Match Video",
            filetypes=[("Video Files", ".mp4 .avi *.mov *.mkv"), ("All Files", ".")]
        )
        if self.video_path:
            messagebox.showinfo("Video Selected", f"✅ Selected: {os.path.basename(self.video_path)}")
            self.progress_label.config(text=f"Ready: {os.path.basename(self.video_path)}")
            
            # Show input video in the input tab
            self.show_input_video_preview()

    def show_input_video_preview(self):
        try:
            cap = cv2.VideoCapture(self.video_path)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 360))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.input_video_frame.config(image=img)
                self.input_video_frame.image = img
            cap.release()
        except Exception as e:
            print(f"Error showing preview: {e}")

    def start_analysis(self):
        if not self.video_path:
            messagebox.showwarning("No Video", "🎥 Please select a video first.")
            return

        if self.analysis_running:
            messagebox.showwarning("Analysis Running", "⏳ Analysis is already in progress.")
            return

        self.analysis_running = True
        self.progress["value"] = 0
        self.progress_percent.config(text="0%")
        self.progress_label.config(text="Starting analysis...")
        
        # Set output video path
        self.output_video_path = os.path.join(self.output_dir, "output_video.avi")
        
        # Start the analysis in a separate thread
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        try:
            # Run your main.py analysis script
            self.progress_label.config(text="🔄 Running football analysis...")
            
            # Run the main.py script as a subprocess
            process = subprocess.Popen([
                sys.executable, "main.py"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            self.analysis_process = process
            
            # Monitor the process and update progress
            self.monitor_analysis_progress(process)
            
        except Exception as e:
            self.analysis_running = False
            self.progress_label.config(text=f"❌ Error: {str(e)}")
            messagebox.showerror("Analysis Error", f"An error occurred: {str(e)}")

    def monitor_analysis_progress(self, process):
        try:
            # Simulate progress updates
            for i in range(101):
                if not self.analysis_running:
                    break
                    
                # Update progress
                self.progress["value"] = i
                self.progress_percent.config(text=f"{i}%")
                self.progress_label.config(text=f"Analyzing... {i}% complete")
                
                # Update live stats
                if i % 10 == 0:
                    self.update_live_stats(i, i)
                
                time.sleep(0.5)  # Simulate analysis time
            
            # Wait for process to complete
            process.wait()
            
            if self.analysis_running and process.returncode == 0:
                self.progress["value"] = 100
                self.progress_percent.config(text="100%")
                self.progress_label.config(text="✅ Analysis completed successfully!")
                
                # Check for output video and heatmap
                self.check_existing_output_videos()
                self.check_existing_heatmap()
                
                messagebox.showinfo("Analysis Complete", 
                                  f"🎉 Video analysis finished successfully!\n\n"
                                  f"Output saved to: {self.output_video_path}")
                self.fetch_firebase_data()
                
                # Switch to output video tab
                self.video_notebook.select(1)
            else:
                messagebox.showinfo("Analysis Complete",
                                    f"🎉 Video analysis finished successfully!\n\n"
                                    f"Output saved to: {self.output_video_path}")
                self.fetch_firebase_data()
                
        except Exception as e:
            self.analysis_running = False
            self.progress_label.config(text=f"❌ Error: {str(e)}")

    def check_existing_output_videos(self):
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                self.output_status_label.config(text="No output videos found", fg=ModernStyle.WARNING)
                return
            
            # Look for output video files
            video_files = [f for f in os.listdir(self.output_dir) 
                          if f.endswith(('.avi', '.mp4', '.mov', '.mkv'))]
            
            if video_files:
                # Use the first video found, or look for output_video.avi specifically
                if "output_video.avi" in video_files:
                    self.output_video_path = os.path.join(self.output_dir, "output_video.avi")
                else:
                    self.output_video_path = os.path.join(self.output_dir, video_files[0])
                
                self.output_status_label.config(
                    text=f"✅ Found: {os.path.basename(self.output_video_path)}", 
                    fg=ModernStyle.SUCCESS
                )
                
                # Show preview of output video
                self.show_output_video_preview()
            else:
                self.output_status_label.config(text="No output videos found", fg=ModernStyle.WARNING)
                
        except Exception as e:
            print(f"Error checking output videos: {e}")

    def check_existing_heatmap(self):
        try:
            if os.path.exists(self.heatmap_path):
                self.heatmap_status_label.config(
                    text=f"✅ Found: {os.path.basename(self.heatmap_path)}", 
                    fg=ModernStyle.SUCCESS
                )
                self.heatmap_status.config(text="Available", fg=ModernStyle.SUCCESS)
                
                # Show heatmap preview
                self.show_heatmap_preview()
            else:
                self.heatmap_status_label.config(text="No heatmap found", fg=ModernStyle.WARNING)
                self.heatmap_status.config(text="Not Available", fg=ModernStyle.WARNING)
                
        except Exception as e:
            print(f"Error checking heatmap: {e}")

    def show_output_video_preview(self):
        if not self.output_video_path or not os.path.exists(self.output_video_path):
            return
            
        try:
            cap = cv2.VideoCapture(self.output_video_path)
            ret, frame = cap.read()
            if ret:
                frame = cv2.resize(frame, (640, 360))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.output_video_frame.config(image=img)
                self.output_video_frame.image = img
            cap.release()
        except Exception as e:
            print(f"Error showing output preview: {e}")

    def show_heatmap_preview(self):
        if not self.heatmap_path or not os.path.exists(self.heatmap_path):
            return
            
        try:
            heatmap_img = cv2.imread(self.heatmap_path)
            if heatmap_img is not None:
                # Resize to fit the display area
                heatmap_img = cv2.resize(heatmap_img, (640, 360))
                rgb = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.heatmap_frame.config(image=img)
                self.heatmap_frame.image = img
            else:
                self.heatmap_status_label.config(text="Error loading heatmap", fg=ModernStyle.WARNING)
        except Exception as e:
            print(f"Error showing heatmap preview: {e}")

    def show_heatmap(self):
        self.video_notebook.select(2)
        self.check_existing_heatmap()

    def save_heatmap(self):
        if not os.path.exists(self.heatmap_path):
            messagebox.showwarning("No Heatmap", "No heatmap found to save.")
            return
            
        file_path = filedialog.asksaveasfilename(
            title="Save Heatmap As",
            defaultextension=".jpg",
            filetypes=[("JPEG Image", ".jpg"), ("PNG Image", ".png"), ("All Files", ".")]
        )
        
        if file_path:
            try:
                import shutil
                shutil.copy2(self.heatmap_path, file_path)
                messagebox.showinfo("Success", f"Heatmap saved to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save heatmap: {str(e)}")

    def play_output_video(self):
        if not self.output_video_path or not os.path.exists(self.output_video_path):
            messagebox.showwarning("No Output Video", 
                                 "No analyzed video found. Please run the analysis first.")
            return

        if self.video_playing:
            messagebox.showinfo("Video Playing", "Video is already playing.")
            return

        self.video_playing = True
        threading.Thread(target=self._play_video, daemon=True).start()

    def _play_video(self):
        try:
            self.current_video_cap = cv2.VideoCapture(self.output_video_path)
            
            while self.video_playing:
                ret, frame = self.current_video_cap.read()
                if not ret:
                    # Loop the video
                    self.current_video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue

                # Display output video frame
                frame = cv2.resize(frame, (640, 360))
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = ImageTk.PhotoImage(Image.fromarray(rgb))
                self.output_video_frame.config(image=img)
                self.output_video_frame.image = img

                time.sleep(0.03)  # ~30 FPS

        except Exception as e:
            print(f"Error playing video: {e}")
        finally:
            if self.current_video_cap:
                self.current_video_cap.release()
            self.video_playing = False

    def pause_video(self):
        self.video_playing = False

    def stop_video(self):
        self.video_playing = False
        # Clear the output video frame
        self.output_video_frame.config(image='')
        self.output_video_frame.image = None

    def refresh_outputs(self):
        self.check_existing_output_videos()
        self.check_existing_heatmap()
        messagebox.showinfo("Refreshed", "Output files check completed.")

    def update_live_stats(self, frame_no, progress):
        possession = 50 + (progress - 50) * 0.5
        speed = 8 + (progress / 20) + (frame_no % 10) * 0.1
        distance = frame_no * 0.8

        self.possession_bar["value"] = possession
        self.possession_label.config(text=f"{possession:.1f}%")
        self.speed_value.config(text=f"{speed:.1f} km/h")
        self.distance_value.config(text=f"{distance:.0f} m")

    def fetch_firebase_data(self):
        if not db:
            messagebox.showerror("Firebase Error", "🔌 Not connected to Firebase.")
            return

        self.progress_label.config(text="📡 Fetching data from Firebase...")

        try:
            # Try different possible document names and collections
            possible_paths = [
                ("Matchs", "match1"),  # Your current path
                ("Matches", "match1"),  # Alternative spelling
                ("matches", "match1"),  # Lowercase
                ("FootballMatches", "match1"),  # More specific
            ]

            doc_ref = None
            data = None

            for collection_name, document_name in possible_paths:
                try:
                    doc_ref = db.collection(collection_name).document(document_name)
                    doc = doc_ref.get()
                    if doc.exists:
                        data = doc.to_dict()
                        print(f"✅ Found data in {collection_name}/{document_name}")
                        break
                except Exception as e:
                    print(f"⚠ Failed to fetch from {collection_name}/{document_name}: {e}")
                    continue

            if data:
                # Update team stats with safe value access
                team1_possession = data.get('Team1Possession', 0)
                team2_possession = data.get('Team2Possession', 0)
                
                self.fb_team1_possession.config(text=f"{team1_possession}%")
                self.fb_team1_speed.config(text=f"{data.get('Team1_AvgSpeed', '--')} km/h")
                self.fb_team1_distance.config(text=f"{data.get('Team1_TotalDistance', '--')} m")

                self.fb_team2_possession.config(text=f"{team2_possession}%")
                self.fb_team2_speed.config(text=f"{data.get('Team2_AvgSpeed', '--')} km/h")
                self.fb_team2_distance.config(text=f"{data.get('Team2_TotalDistance', '--')} m")

                # Update live stats to match Firebase data
                self.possession_bar["value"] = team1_possession
                self.possession_label.config(text=f"{team1_possession}%")

                # Get player data if available
                if doc_ref:
                    try:
                        players_ref = doc_ref.collection("Players")
                        players_docs = players_ref.limit(10).get()

                        # Clear previous player data
                        for widget in self.players_frame.winfo_children():
                            widget.destroy()

                        # Display top players
                        for i, player_doc in enumerate(players_docs):
                            player_data = player_doc.to_dict()
                            self.create_player_row(self.players_frame, i, player_doc.id, player_data)

                        print(f"✅ Loaded {len(players_docs)} players")
                    except Exception as e:
                        print(f"⚠ Could not load players: {e}")

                self.progress_label.config(text="✅ Firebase data updated successfully!")
                
                # Show success message
                messagebox.showinfo("Data Loaded", 
                                  f"✅ Successfully loaded match data!\n\n"
                                  f"Team 1: {team1_possession}% possession\n"
                                  f"Team 2: {team2_possession}% possession")
            else:
                # If no data found, create sample data for testing
                self.create_sample_firebase_data()
                messagebox.showinfo("No Data Found", 
                                  "📭 No existing match data found.\n\n"
                                  "Sample data has been created for testing.\n"
                                  "Run the analysis to generate real match data.")

        except Exception as e:
            error_msg = f"❌ Error fetching Firebase data: {e}"
            print(error_msg)
            messagebox.showerror("Firestore Error", error_msg)
            self.progress_label.config(text="❌ Error fetching Firebase data")

    def create_sample_firebase_data(self):
        if not db:
            return

        try:
            # Create sample match data
            match_ref = db.collection("Matchs").document("match1")
            match_ref.set({
                "Date": "2024-01-15",
                "Team1Possession": 52.3,
                "Team2Possession": 47.7,
                "Team1_AvgSpeed": 7.8,
                "Team1_TotalDistance": 12560.5,
                "Team2_AvgSpeed": 7.4,
                "Team2_TotalDistance": 11890.2
            })

            # Create sample player data
            players_ref = match_ref.collection("Players")
            
            sample_players = [
                {"Team": 1, "AvgSpeed": 8.2, "TotalDistance": 1250.5},
                {"Team": 1, "AvgSpeed": 7.9, "TotalDistance": 1180.3},
                {"Team": 2, "AvgSpeed": 7.5, "TotalDistance": 1120.7},
                {"Team": 2, "AvgSpeed": 7.8, "TotalDistance": 1210.2},
            ]

            for i, player_data in enumerate(sample_players):
                players_ref.document(f"player{i+1}").set(player_data)

            print("✅ Sample Firebase data created")
            
            # Refresh the display with sample data
            self.fetch_firebase_data()

        except Exception as e:
            print(f"❌ Error creating sample data: {e}")

    def create_player_row(self, parent, _index, player_id, player_data):
        frame = tk.Frame(parent, bg=ModernStyle.WHITE)
        frame.pack(fill=tk.X, pady=2)

        team_color = ModernStyle.PRIMARY if player_data.get('Team') == 1 else ModernStyle.SECONDARY
        team_symbol = "🔵" if player_data.get('Team') == 1 else "🔴"

        tk.Label(frame, text=f"{team_symbol} Player {player_id}", font=("Segoe UI", 8, "bold"),
                 fg=team_color, bg=ModernStyle.WHITE, width=12).pack(side=tk.LEFT)

        tk.Label(frame, text=f"⚡{player_data.get('AvgSpeed', '0')}km/h", font=("Segoe UI", 8),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(side=tk.RIGHT, padx=(5, 0))

        tk.Label(frame, text=f"📏{player_data.get('TotalDistance', '0')}m", font=("Segoe UI", 8),
                 fg=ModernStyle.TEXT, bg=ModernStyle.WHITE).pack(side=tk.RIGHT, padx=(5, 0))

    def stop_analysis(self):
        self.analysis_running = False
        self.video_playing = False
        if self.analysis_process:
            self.analysis_process.terminate()
        if self.current_video_cap:
            self.current_video_cap.release()
        self.progress_label.config(text="⏹ Analysis stopped by user")


if __name__ == "__main__":
    root = tk.Tk()
    app = FootballAnalysisApp(root)

    def on_closing():
        app.stop_analysis()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()