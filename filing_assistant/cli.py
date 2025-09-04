from __future__ import annotations
import json, typer, os
from rich import print, box
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .store import load_store, save_store
from .trainer import pair_training_files
from .enhanced_trainer import enhanced_learn_from_pair, enhanced_merge_patterns
from .identifier import identify_required_columns, enhanced_identify_required_columns

# Add the enhanced header detector import
try:
    from .enhanced_header_detector import EnhancedHeaderDetector
    ENHANCED_HEADERS_AVAILABLE = True
except ImportError:
    ENHANCED_HEADERS_AVAILABLE = False
    print("[yellow]⚠️  Enhanced header detection not available. Install required dependencies.[/yellow]")

app = typer.Typer(add_completion=False)

def display_training_results(training_results: list, out_store: str, total_pairs: int):
    """Display comprehensive training results with file, sheet, and column details"""
    print()
    print("[bold green]🎉 Enhanced Training Completed Successfully![/bold green]")
    print()
    
    if not training_results:
        print("[yellow]⚠️  No fillable columns were identified during training.[/yellow]")
        return
    
    # Summary statistics
    total_sheets = len(set(result["sheet"] for result in training_results))
    total_columns = sum(result["count"] for result in training_results)
    
    # Create summary panel
    summary_text = f"""[bold]📊 Training Summary:[/bold]
    
• [cyan]Pairs Processed:[/cyan] {total_pairs}
• [cyan]Sheets Learned:[/cyan] {total_sheets}
• [cyan]Fillable Columns Identified:[/cyan] {total_columns}
• [cyan]Pattern Store:[/cyan] {out_store}"""
    
    print(Panel(summary_text, title="🎯 Enhanced Training Results", border_style="green"))
    print()
    
    # Detailed results table
    print("[bold blue]📋 Detailed Training Results:[/bold blue]")
    print()
    
    table = Table(title="🎯 Fillable Columns Learned", box=box.ROUNDED, show_lines=True)
    table.add_column("Training Pair", style="cyan", no_wrap=True)
    table.add_column("Sheet Name", style="magenta")
    table.add_column("Columns", justify="center", style="green")
    table.add_column("Fillable Column Names", style="white")
    table.add_column("Headers", justify="center", style="blue")
    
    # Group by pair for better organization
    by_pair = {}
    for result in training_results:
        pair = result["pair"]
        if pair not in by_pair:
            by_pair[pair] = []
        by_pair[pair].append(result)
    
    for pair_name, pair_results in by_pair.items():
        for i, result in enumerate(pair_results):
            # Only show pair name for the first row of each pair
            pair_display = pair_name if i == 0 else ""
            
            # Format column names for display (limit length)
            columns_text = ", ".join(result["columns"])
            if len(columns_text) > 60:
                columns_text = columns_text[:57] + "..."
            
            # Enhanced headers indicator
            headers_indicator = "🤖" if result.get("enhanced_headers", False) else "📊"
            
            table.add_row(
                pair_display,
                result["sheet"],
                str(result["count"]),
                columns_text,
                headers_indicator
            )
    
    print(table)
    print()
    
    # Sheet-wise summary
    sheet_summary = {}
    for result in training_results:
        sheet = result["sheet"]
        if sheet not in sheet_summary:
            sheet_summary[sheet] = {"pairs": set(), "total_columns": 0}
        sheet_summary[sheet]["pairs"].add(result["pair"])
        sheet_summary[sheet]["total_columns"] += result["count"]
    
    print("[bold blue]📊 Sheet-wise Learning Summary:[/bold blue]")
    print()
    
    summary_table = Table(box=box.SIMPLE)
    summary_table.add_column("Sheet Name", style="magenta")
    summary_table.add_column("Training Pairs", justify="center", style="cyan")
    summary_table.add_column("Total Columns", justify="center", style="green")
    
    for sheet, data in sorted(sheet_summary.items()):
        summary_table.add_row(
            sheet,
            str(len(data["pairs"])),
            str(data["total_columns"])
        )
    
    print(summary_table)
    print()
    print(f"[green]✅ Enhanced patterns saved to:[/green] [bold]{out_store}[/bold]")
    print(f"[blue]💡 Use these patterns for identification with:[/blue]")
    print(f"   [dim]python -m filing_assistant.cli identify --file empty_file.json --store {out_store}[/dim]")
    print()

@app.command()
def train(data_dir: str = typer.Option(..., help="Folder with training JSON files"),
          out_store: str = typer.Option("patterns_store.json", help="Where to save AI-enhanced patterns"),
          sheet: str = typer.Option(None, help="Specific sheet name to learn (auto-detects all data sheets)"),
          verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed processing information")):
    """AI-Enhanced Training - learns fillable patterns with OpenAI-powered business header detection"""
    
    # Check for OpenAI availability
    if not ENHANCED_HEADERS_AVAILABLE:
        print("[red]❌ Error: OpenAI integration required for AI-enhanced Filing Assistant[/red]")
        print("[yellow]Please install OpenAI: pip install openai[/yellow]") 
        print("[yellow]And set API key: export OPENAI_API_KEY='your-key'[/yellow]")
        raise typer.Exit(code=1)
    
    print(f"[blue]🚀 Starting AI-Enhanced Training on directory:[/blue] {data_dir}")
    if sheet:
        print(f"[blue]📊 Target sheet:[/blue] {sheet}")
    else:
        print(f"[blue]📊 Auto-detecting data sheets in each file[/blue]")
    print(f"[blue]💾 Output store:[/blue] {out_store}")
    print(f"[blue]🤖 AI Enhancement:[/blue] OpenAI-powered business header detection ENABLED")
    print()
    
    # Discover and display all available pairs
    pairs = pair_training_files(data_dir, verbose=verbose)
    if not pairs:
        print("[yellow]❌ No Empty/Filled pairs found.[/yellow]")
        print("Expected filename pattern: *Empty*_structured.json + *Filled*_structured.json")
        raise typer.Exit(code=1)
    
    # Display discovered pairs
    print(f"[green]✅ Discovered {len(pairs)} training pairs:[/green]")
    print()
    
    table = Table(title="📂 Training File Pairs Discovered", box=box.ROUNDED)
    table.add_column("Pair", justify="center", style="cyan", no_wrap=True)
    table.add_column("Empty File", style="green")
    table.add_column("Filled File", style="blue")
    
    for i, (empty, filled) in enumerate(pairs, 1):
        empty_name = os.path.basename(empty)
        filled_name = os.path.basename(filled)
        table.add_row(str(i), empty_name, filled_name)
    
    print(table)
    print()
    
    # Enhanced training with detailed results
    print(f"[blue]🧠 Processing {len(pairs)} pairs using Enhanced Training method...[/blue]")
    print()
    
    store = {"sheets": {}}
    training_results = []
    
    for i, (empty, filled) in enumerate(pairs, 1):
        pair_name = f"{os.path.basename(empty).replace('_structured.json', '').replace(' Empty', '')}"
        print(f"[dim]🔄 Processing pair {i}/{len(pairs)}: {pair_name}[/dim]")
        
        try:
            learned = enhanced_learn_from_pair(empty, filled, sheet, verbose=verbose, use_enhanced_headers=True)
            store = enhanced_merge_patterns(store, learned)
            
            # Collect training results for summary
            for sheet_name, sheet_data in learned.get("sheets", {}).items():
                fillable_columns = sheet_data.get("columns_to_fill", [])
                enhanced_headers_used = sheet_data.get("enhanced_headers_used", False)
                if fillable_columns:
                    training_results.append({
                        "pair": pair_name,
                        "sheet": sheet_name,
                        "columns": fillable_columns,
                        "count": len(fillable_columns),
                        "enhanced_headers": enhanced_headers_used
                    })
        except Exception as e:
            print(f"[red]❌ Error processing pair {i}: {e}[/red]")
            continue
    
    # Save results
    save_store(out_store, store)
    
    # Display comprehensive training results
    display_training_results(training_results, out_store, len(pairs))

@app.command()
def identify(file: str = typer.Option(..., help="New empty JSON file"),
             store: str = typer.Option("patterns_store.json", help="AI-enhanced patterns store"),
             sheet: str = typer.Option(None, help="Sheet name to identify (auto-detect if not specified)"),
             out: str = typer.Option(None, help="Optional path to write JSON result"),
             threshold: float = typer.Option(0.7, help="Confidence threshold for auto-accept mapping"),
             verbose: bool = typer.Option(False, help="Show detailed processing information")):
    """AI-Enhanced Identification - identifies fillable columns with cross-sheet pattern analysis and OpenAI headers"""
    
    # Check for OpenAI availability
    if not ENHANCED_HEADERS_AVAILABLE:
        print("[red]❌ Error: OpenAI integration required for AI-enhanced Filing Assistant[/red]")
        print("[yellow]Please install OpenAI: pip install openai[/yellow]") 
        print("[yellow]And set API key: export OPENAI_API_KEY='your-key'[/yellow]")
        raise typer.Exit(code=1)
    
    st = load_store(store)
    
    if verbose:
        print(f"[bold blue]🔍 AI-Enhanced Identification for:[/bold blue] {file}")
        if sheet:
            print(f"[dim]📋 Target sheet: {sheet}[/dim]")
        else:
            print(f"[dim]📋 Auto-detecting all sheets[/dim]")
        print(f"[dim]📊 Confidence threshold: {threshold}[/dim]")
        print(f"[dim]🤖 Enhanced header detection: ENABLED[/dim]")
        print(f"[dim]🔄 Cross-sheet pattern analysis: ENABLED[/dim]")
        print()
    
    # Always use cross-sheet analysis with enhanced headers
    from .cross_sheet_analyzer import cross_sheet_identify_required_columns
    result = cross_sheet_identify_required_columns(file, st, sheet, threshold, True)
    is_cross_sheet = True
    
    # Handle cross-sheet results format
    if is_cross_sheet and "primary_results" in result:
        primary_sheet = result.get("primary_sheet")
        primary_results = result.get("primary_results", {})
        
        if verbose and primary_sheet:
            patterns_analyzed = result.get("summary", {}).get("patterns_analyzed", 0)
            print(f"[green]🔄 Cross-sheet analysis completed:[/green] Analyzed {patterns_analyzed} pattern sources")
            print(f"[green]✨ Best sheet identified:[/green] {primary_sheet}")
        
        # Convert to standard format for display
        result = {
            "sheets": {primary_sheet: primary_results},
            "summary": result.get("summary", {}),
            "cross_sheet_analysis": True
        }
    
    # Handle error cases
    if "error" in result:
        print(f"[red]❌ Error:[/red] {result['error']}")
        if "available_sheets" in result:
            print(f"[yellow]Available sheets in file:[/yellow] {', '.join(result['available_sheets'])}")
        if "learned_sheets" in result:
            print(f"[yellow]Learned sheets in patterns:[/yellow] {', '.join(result['learned_sheets'])}")
        return
    
    # Display results for each sheet
    for sheet_name, sheet_data in result.get("sheets", {}).items():
        if "error" in sheet_data:
            print(f"[red]❌ {sheet_name}:[/red] {sheet_data['error']}")
            continue
        
        # Show header enhancement info if available
        enhancement_info = sheet_data.get("header_enhancement", {})
        if enhancement_info.get("enhanced"):
            enhancement_confidence = enhancement_info.get("confidence", 0)
            print(f"[green]🤖 Enhanced Headers Used:[/green] {sheet_name} (Confidence: {enhancement_confidence:.1%})")
            
        tbl = Table(title=f"Columns to Fill — {sheet_name}", box=box.SIMPLE_HEAVY)
        tbl.add_column("Pos", justify="right")
        tbl.add_column("Header")
        tbl.add_column("Label")
        tbl.add_column("Conf", justify="right")
        tbl.add_column("Method")
        tbl.add_column("Decision")
        tbl.add_column("Enhanced", justify="center")
        tbl.add_column("Sources", justify="center")
        
        # Add fillable columns
        for r in sheet_data.get("columns", []):
            method_color = "green" if r.get("learned_fillable") else "blue"
            method_text = f"[{method_color}]{r['verified_by']}[/{method_color}]"
            
            row_data = [
                str(r["position"]), 
                r["header"], 
                r["label"], 
                f"{r['confidence']:.2f}",
                method_text,
                r["decision"]
            ]
            
            # Always show enhanced headers indicator
            enhanced_marker = "🤖" if r.get("enhanced_header") else "📊"
            row_data.append(enhanced_marker)
            
            # Always show source patterns count
            source_patterns = r.get("source_patterns", [])
            if source_patterns:
                source_indicator = f"🔄{len(source_patterns)}"
            else:
                source_indicator = "📋1"
            row_data.append(source_indicator)
            
            tbl.add_row(*row_data)
        
        # Add unknown columns if any
        if sheet_data.get("unknowns"):
            tbl.add_section()
            for r in sheet_data.get("unknowns", []):
                method_color = "dim" if r.get("learned_fillable") else "dim"
                method_text = f"[{method_color}]{r['verified_by']}[/{method_color}]"
                
                row_data = [
                    str(r["position"]), 
                    r["header"], 
                    r["label"], 
                    f"{r['confidence']:.2f}",
                    method_text,
                    f"[dim]{r['decision']}[/dim]"
                ]
                
                # Always show enhanced headers indicator
                enhanced_marker = "🤖" if r.get("enhanced_header") else "📊"
                row_data.append(f"[dim]{enhanced_marker}[/dim]")
                
                # Always show source patterns count
                source_patterns = r.get("source_patterns", [])
                if source_patterns:
                    source_indicator = f"🔄{len(source_patterns)}"
                else:
                    source_indicator = "📋1"
                row_data.append(f"[dim]{source_indicator}[/dim]")
                
                tbl.add_row(*row_data)
        
        print(tbl)
        
        if verbose:
            total_headers = sheet_data.get("total_headers", 0)
            analyzed = sheet_data.get("analyzed_columns", 0)
            fillable = len(sheet_data.get("columns", []))
            print(f"[dim]📊 {sheet_name}: {total_headers} headers, {analyzed} analyzed, {fillable} fillable[/dim]")
        print()
    
    # Display summary
    summary = result.get("summary", {})
    if summary:
        print(f"[bold green]📊 Summary:[/bold green]")
        print(f"  [bold white]Sheets processed:[/bold white] {summary['sheets_processed']}")
        print(f"  [bold white]Fillable columns:[/bold white] {summary['total_fillable_columns']}")
        print(f"  [bold white]Unknown columns:[/bold white] {summary['total_unknown_columns']}")
        
        # Cross-sheet analysis info
        if summary.get("cross_sheet_analysis"):
            patterns_analyzed = summary.get("patterns_analyzed", 0)
            best_sheet = summary.get("best_sheet", "unknown")
            print(f"  [bold cyan]Cross-sheet analysis:[/bold cyan] {patterns_analyzed} pattern sources analyzed 🔄")
            print(f"  [bold cyan]Best sheet identified:[/bold cyan] {best_sheet}")
        
        # Enhanced headers info
        if summary.get("enhanced_headers_used") or summary.get("enhancement_used"):
            print(f"  [bold cyan]Enhanced headers:[/bold cyan] ENABLED 🤖")
        else:
            print(f"  [bold dim]Enhanced headers:[/bold dim] Standard 📊")
    
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[green]✅ Wrote identify result to[/green] {out}")

@app.command()
def update(store: str = typer.Option(..., help="Patterns store to update"),
           user_labels: str = typer.Option(..., help="JSON file with user-provided column_labels by sheet")):
    st = load_store(store)
    with open(user_labels, "r", encoding="utf-8") as f:
        upd = json.load(f)
    for sheet, payload in upd.items():
        target = st.setdefault("sheets", {}).setdefault(sheet, {"header_map": {}, "columns_to_fill": [], "column_positions": {}, "verifications": {}})
        labels = payload.get("column_labels", {})
        for raw, norm in labels.items():
            target["header_map"].setdefault(raw, [])
            if raw not in target["columns_to_fill"]:
                target["columns_to_fill"].append(raw)
            target["verifications"][raw] = {"label": norm, "confidence": 1.0, "method": "user"}
    save_store(store, st)
    print(f"[green]Updated patterns store[/green] {store}")

if __name__ == "__main__":
    app()
