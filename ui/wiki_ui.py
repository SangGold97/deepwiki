import streamlit as st
import requests
import os
import json
import base64
from pathlib import Path

# Cấu hình page và title
st.set_page_config(page_title="DeepWiki Generator", layout="wide")
st.title("DeepWiki Generator")

# Initialize session state variables if they don't exist
if 'wiki_generated' not in st.session_state:
    st.session_state.wiki_generated = False
if 'wiki_pages' not in st.session_state:
    st.session_state.wiki_pages = []
if 'repo_path' not in st.session_state:
    st.session_state.repo_path = ""
if 'model_provider' not in st.session_state:
    st.session_state.model_provider = ""
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = ""
if 'excluded_dirs_list' not in st.session_state:
    st.session_state.excluded_dirs_list = []
if 'excluded_files_list' not in st.session_state:
    st.session_state.excluded_files_list = []

# Sidebar cho cấu hình
with st.sidebar:
    st.header("Configuration")
    
    # Chọn đường dẫn repository
    repo_path = st.text_input("Local Repository Path", 
                              placeholder="Enter absolute path to your repository")
    
    # Chọn mô hình OpenAI
    st.subheader("Model Selection")
    model_provider = st.selectbox("Provider", ["openai", "google", "ollama", "openrouter"])
    
    # Tùy chỉnh model options dựa trên provider
    if model_provider == "openai":
        model_options = ["gpt-4o", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]
    elif model_provider == "google":
        model_options = ["gemini-1.5-pro", "gemini-1.0-pro"]
    elif model_provider == "ollama":
        model_options = ["llama3", "mixtral", "mistral"]
    else:  # openrouter
        model_options = ["meta-llama/llama-3-70b-8192", "anthropic/claude-3-opus", "anthropic/claude-3-sonnet"]
    
    selected_model = st.selectbox("Model", model_options)
    
    # Kiểu wiki (Comprehensive hoặc Concise)
    wiki_type = st.radio("Wiki Type", ["Comprehensive", "Concise"])
    
    # API Key cho OpenAI
    api_key = st.text_input("OpenAI API Key (or relevant provider key)", 
                           type="password", 
                           help="Enter your API key for the selected provider")
    
    # Thư mục loại trừ
    excluded_dirs = st.text_area("Excluded Directories (one per line)", 
                                placeholder="node_modules\n.git\n.vscode")
    
    # File loại trừ
    excluded_files = st.text_area("Excluded Files (one per line)", 
                                 placeholder="*.log\n*.tmp\n*.pyc")

# Main area - Form để submit yêu cầu
st.header("Generate Wiki for your Repository")

if st.button("Generate Wiki", type="secondary"):
    if not repo_path:
        st.error("Please provide a repository path")
    else:
        # Kiểm tra đường dẫn repository
        if not os.path.exists(repo_path):
            st.error(f"Repository path does not exist: {repo_path}")
        else:
            with st.spinner("Analyzing repository structure..."):
                try:
                    # Step 1: Analyze Repository Structure
                    # Tạo cây thư mục
                    def get_file_tree(path, excluded_dirs_list=None, excluded_files_list=None):
                        if excluded_dirs_list is None:
                            excluded_dirs_list = []
                        if excluded_files_list is None:
                            excluded_files_list = []
                            
                        result = []
                        root_path = Path(path)
                        
                        for item in root_path.glob("**/*"):
                            # Chuyển đường dẫn tương đối
                            rel_path = item.relative_to(root_path)
                            
                            # Kiểm tra nếu thư mục/file nên bị loại trừ
                            skip = False
                            for excluded in excluded_dirs_list:
                                if excluded in str(rel_path):
                                    skip = True
                                    break
                            if skip:
                                continue
                                
                            # Thêm vào danh sách
                            if item.is_file():
                                result.append(str(rel_path))
                                
                        return "\n".join(result)
                    
                    # Tách danh sách thư mục/file loại trừ
                    excluded_dirs_list = excluded_dirs.split("\n") if excluded_dirs else []
                    excluded_files_list = excluded_files.split("\n") if excluded_files else []
                    
                    # Lấy file tree
                    file_tree = get_file_tree(repo_path, excluded_dirs_list, excluded_files_list)
                    
                    # Đọc README.md nếu có
                    readme_content = ""
                    readme_path = os.path.join(repo_path, "README.md")
                    if os.path.exists(readme_path):
                        with open(readme_path, "r", encoding="utf-8") as f:
                            readme_content = f.read()
                    
                    # Chuẩn bị dữ liệu để gửi đến API
                    is_comprehensive = wiki_type == "Comprehensive"
                    repo_name = os.path.basename(os.path.normpath(repo_path))
                    repo_owner = os.path.basename(os.path.dirname(os.path.normpath(repo_path)))
                    
                    # Step 2: Tạo prompt cho wiki structure
                    structure_prompt = f"""Analyze this GitHub repository {repo_owner}/{repo_name} and create a wiki structure for it.

1. The complete file tree of the project:
<file_tree>
{file_tree}
</file_tree>

2. The README file of the project:
<readme>
{readme_content}
</readme>

I want to create a wiki for this repository. Determine the most logical structure for a wiki based on the repository's content.

When designing the wiki structure, include pages that would benefit from visual diagrams, such as:
- Architecture overviews
- Data flow descriptions
- Component relationships
- Process workflows
- State machines
- Class hierarchies

{
    '''
Create a structured wiki with the following main sections:
- Overview (general information about the project)
- System Architecture (how the system is designed)
- Core Features (key functionality)
- Data Management/Flow: If applicable, how data is stored, processed, accessed, and managed (e.g., database schema, data pipelines, state management).
- Frontend Components (UI elements, if applicable.)
- Backend Systems (server-side components)
- Model Integration (AI model connections)
- Deployment/Infrastructure (how to deploy, what's the infrastructure like)
- Extensibility and Customization: If the project architecture supports it, explain how to extend or customize its functionality (e.g., plugins, theming, custom modules, hooks).

Each section should contain relevant pages. For example, the "Frontend Components" section might include pages for "Home Page", "Repository Wiki Page", "Ask Component", etc.

Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <sections>
    <section id="section-1">
      <title>[Section title]</title>
      <pages>
        <page_ref>page-1</page_ref>
        <page_ref>page-2</page_ref>
      </pages>
      <subsections>
        <section_ref>section-2</section_ref>
      </subsections>
    </section>
    <!-- More sections as needed -->
  </sections>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
      <parent_section>section-1</parent_section>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>
''' if is_comprehensive else '''
Return your analysis in the following XML format:

<wiki_structure>
  <title>[Overall title for the wiki]</title>
  <description>[Brief description of the repository]</description>
  <pages>
    <page id="page-1">
      <title>[Page title]</title>
      <description>[Brief description of what this page will cover]</description>
      <importance>high|medium|low</importance>
      <relevant_files>
        <file_path>[Path to a relevant file]</file_path>
        <!-- More file paths as needed -->
      </relevant_files>
      <related_pages>
        <related>page-2</related>
        <!-- More related page IDs as needed -->
      </related_pages>
    </page>
    <!-- More pages as needed -->
  </pages>
</wiki_structure>
'''}

IMPORTANT FORMATTING INSTRUCTIONS:
- Return ONLY the valid XML structure specified above
- DO NOT wrap the XML in markdown code blocks (no \`\`\` or \`\`\`xml)
- DO NOT include any explanation text before or after the XML
- Ensure the XML is properly formatted and valid
- Start directly with <wiki_structure> and end with </wiki_structure>

IMPORTANT:
1. Create {8-12 if is_comprehensive else 4-6} pages that would make a {wiki_type.lower()} wiki for this repository
2. Each page should focus on a specific aspect of the codebase (e.g., architecture, key features, setup)
3. The relevant_files should be actual files from the repository that would be used to generate that page
4. Return ONLY valid XML with the structure specified above, with no markdown code block delimiters"""

                    # Step 3: Send request to API
                    api_url = "http://localhost:8001/chat/completions/stream"
                    
                    structure_request_body = {
                        "repo_url": f"file://{repo_path}",
                        "type": "local",
                        "provider": model_provider,
                        "model": selected_model,
                        "excluded_dirs": "\n".join(excluded_dirs_list) if excluded_dirs_list else None,
                        "excluded_files": "\n".join(excluded_files_list) if excluded_files_list else None,
                        "messages": [{"role": "user", "content": structure_prompt}]
                    }
                    
                    # Thêm API key nếu được nhập
                    if api_key:
                        os.environ["OPENAI_API_KEY"] = api_key
                    
                    # Gọi API để phân tích cấu trúc
                    structure_response = requests.post(
                        api_url, 
                        json=structure_request_body,
                        stream=True
                    )
                    
                    if structure_response.status_code != 200:
                        st.error(f"API Error: {structure_response.status_code}")
                        st.error(structure_response.text)
                    else:
                        # Hiển thị kết quả phân tích cấu trúc
                        structure_result = ""
                        structure_placeholder = st.empty()
                        
                        for chunk in structure_response.iter_content(chunk_size=1024):
                            if chunk:
                                structure_result += chunk.decode('utf-8')
                                structure_placeholder.text(structure_result)
                        
                        # Xử lý chuỗi XML trả về
                        xml_match = structure_result.strip()
                        
                        try:
                            # Parse XML
                            import xml.etree.ElementTree as ET
                            
                            # Fix common XML issues
                            xml_match = xml_match.replace("&", "&amp;")
                            root = ET.fromstring(xml_match)
                            
                            # Extract wiki structure
                            wiki_title = root.find("title").text
                            wiki_description = root.find("description").text
                            
                            # Tạo container cho Wiki Structure
                            st.success("Wiki structure generated successfully!")
                            st.header(wiki_title)
                            st.write(wiki_description)                                # Hiển thị pages
                            pages = root.findall(".//page")
                            st.subheader("Wiki Pages")
                            
                            wiki_pages = []
                            for page in pages:
                                page_id = page.attrib.get('id', '')
                                page_title = page.find("title").text
                                page_description = page.find("description").text if page.find("description") is not None else ""
                                page_importance = page.find("importance").text if page.find("importance") is not None else "medium"
                                
                                relevant_files = []
                                for file_path in page.findall(".//file_path"):
                                    if file_path.text:
                                        relevant_files.append(file_path.text)
                                
                                wiki_pages.append({
                                    "id": page_id,
                                    "title": page_title,
                                    "description": page_description,
                                    "importance": page_importance,
                                    "filePaths": relevant_files,
                                    "relatedPages": []
                                })
                                
                                with st.expander(f"{page_title} ({page_importance.upper()})"):
                                    st.write(page_description)
                                    st.write("**Relevant Files:**")
                                    for file in relevant_files:
                                        st.code(file, language="")
                            
                            # Save important data to session state
                            st.session_state.wiki_generated = True
                            st.session_state.wiki_pages = wiki_pages
                            st.session_state.repo_path = repo_path
                            st.session_state.model_provider = model_provider
                            st.session_state.selected_model = selected_model
                            st.session_state.excluded_dirs_list = excluded_dirs_list
                            st.session_state.excluded_files_list = excluded_files_list
                            
                            # Generate Content button is moved outside the first if statement
                            
                            # Generate Content button is moved outside the first if statement
                        except Exception as e:
                            st.error(f"Error parsing XML: {str(e)}")
                            st.code(xml_match)
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Add code to display wiki pages and generate content outside the Generate Wiki button
if st.session_state.wiki_generated:
    st.header("Wiki Pages")
    
    # Display wiki pages from session state
    for page in st.session_state.wiki_pages:
        with st.expander(f"{page['title']} ({page['importance'].upper()})"):
            st.write(page['description'])
            st.write("**Relevant Files:**")
            for file in page['filePaths']:
                st.code(file, language="")
    
    # Generate Content for All Pages button (independent from previous button)
    if st.button("Generate Content for All Pages", key="generate_content"):
        with st.spinner("Generating page content... This may take several minutes."):
            for page in st.session_state.wiki_pages:
                st.write(f"Generating content for: **{page['title']}**")
                
                # Tạo prompt cho nội dung page
                content_prompt = f"""You are an expert technical writer and software architect.
Your task is to generate a comprehensive and accurate technical wiki page in Markdown format about a specific feature, system, or module within a given software project.

You will be given:
1. The "[WIKI_PAGE_TOPIC]" for the page you need to create.
2. A list of "[RELEVANT_SOURCE_FILES]" from the project that you MUST use as the sole basis for the content. You have access to the full content of these files. You MUST use AT LEAST 5 relevant source files for comprehensive coverage - if fewer are provided, search for additional related files in the codebase.

CRITICAL STARTING INSTRUCTION:
The very first thing on the page MUST be a `<details>` block listing ALL the `[RELEVANT_SOURCE_FILES]` you used to generate the content. There MUST be AT LEAST 5 source files listed - if fewer were provided, you MUST find additional related files to include.
Format it exactly like this:
<details>
<summary>Relevant source files</summary>

The following files were used as context for generating this wiki page:

{chr(10).join([f"- [{f}]({f})" for f in page['filePaths']])}
<!-- Add additional relevant files if fewer than 5 were provided -->
</details>

Immediately after the `<details>` block, the main title of the page should be a H1 Markdown heading: `# {page['title']}`.

Based ONLY on the content of the `[RELEVANT_SOURCE_FILES]`:

1.  **Introduction:** Start with a concise introduction (1-2 paragraphs) explaining the purpose, scope, and high-level overview of "{page['title']}" within the context of the overall project. If relevant, and if information is available in the provided files, link to other potential wiki pages using the format `[Link Text](#page-anchor-or-id)`.

2.  **Detailed Sections:** Break down "{page['title']}" into logical sections using H2 (`##`) and H3 (`###`) Markdown headings. For each section:
    *   Explain the architecture, components, data flow, or logic relevant to the section's focus, as evidenced in the source files.
    *   Identify key functions, classes, data structures, API endpoints, or configuration elements pertinent to that section.

3.  **Mermaid Diagrams:**
    *   EXTENSIVELY use Mermaid diagrams (e.g., `flowchart TD`, `sequenceDiagram`, `classDiagram`, `erDiagram`, `graph TD`) to visually represent architectures, flows, relationships, and schemas found in the source files.
    *   Ensure diagrams are accurate and directly derived from information in the `[RELEVANT_SOURCE_FILES]`.
    *   Provide a brief explanation before or after each diagram to give context.
    *   CRITICAL: All diagrams MUST follow strict vertical orientation:
       - Use "graph TD" (top-down) directive for flow diagrams
       - NEVER use "graph LR" (left-right)
       - Maximum node width should be 3-4 words
       - For sequence diagrams:
         - Start with "sequenceDiagram" directive on its own line
         - Define ALL participants at the beginning
         - Use descriptive but concise participant names
         - Use the correct arrow types:
           - ->> for request/asynchronous messages
           - -->> for response messages
           - -x for failed messages
         - Include activation boxes using +/- notation
         - Add notes for clarification using "Note over" or "Note right of"

4.  **Tables:**
    *   Use Markdown tables to summarize information such as:
        *   Key features or components and their descriptions.
        *   API endpoint parameters, types, and descriptions.
        *   Configuration options, their types, and default values.
        *   Data model fields, types, constraints, and descriptions.

5.  **Code Snippets:**
    *   Include short, relevant code snippets (e.g., Python, Java, JavaScript, SQL, JSON, YAML) directly from the `[RELEVANT_SOURCE_FILES]` to illustrate key implementation details, data structures, or configurations.
    *   Ensure snippets are well-formatted within Markdown code blocks with appropriate language identifiers.

6.  **Source Citations (EXTREMELY IMPORTANT):**
    *   For EVERY piece of significant information, explanation, diagram, table entry, or code snippet, you MUST cite the specific source file(s) and relevant line numbers from which the information was derived.
    *   Place citations at the end of the paragraph, under the diagram/table, or after the code snippet.
    *   Use the exact format: `Sources: [filename.ext:start_line-end_line]()` for a range, or `Sources: [filename.ext:line_number]()` for a single line. Multiple files can be cited: `Sources: [file1.ext:1-10](), [file2.ext:5](), [dir/file3.ext]()` (if the whole file is relevant and line numbers are not applicable or too broad).
    *   If an entire section is overwhelmingly based on one or two files, you can cite them under the section heading in addition to more specific citations within the section.
    *   IMPORTANT: You MUST cite AT LEAST 5 different source files throughout the wiki page to ensure comprehensive coverage.

7.  **Technical Accuracy:** All information must be derived SOLELY from the `[RELEVANT_SOURCE_FILES]`. Do not infer, invent, or use external knowledge about similar systems or common practices unless it's directly supported by the provided code. If information is not present in the provided files, do not include it or explicitly state its absence if crucial to the topic.

8.  **Clarity and Conciseness:** Use clear, professional, and concise technical language suitable for other developers working on or learning about the project. Avoid unnecessary jargon, but use correct technical terms where appropriate.

9.  **Conclusion/Summary:** End with a brief summary paragraph if appropriate for "{page['title']}", reiterating the key aspects covered and their significance within the project.

Remember:
- Ground every claim in the provided source files.
- Prioritize accuracy and direct representation of the code's functionality and structure.
- Structure the document logically for easy understanding by other developers."""

                # Gửi request đến API
                api_url = "http://localhost:8001/chat/completions/stream"
                content_request_body = {
                    "repo_url": f"file://{st.session_state.repo_path}",
                    "type": "local",
                    "provider": st.session_state.model_provider,
                    "model": st.session_state.selected_model,
                    "excluded_dirs": "\n".join(st.session_state.excluded_dirs_list) if st.session_state.excluded_dirs_list else None,
                    "excluded_files": "\n".join(st.session_state.excluded_files_list) if st.session_state.excluded_files_list else None,
                    "messages": [{"role": "user", "content": content_prompt}]
                }
                
                st.write(f"Sending API request for: **{page['title']}**")
                content_response = requests.post(
                    api_url, 
                    json=content_request_body,
                    stream=True
                )
                
                st.write(f"API response status: {content_response.status_code}")
                if content_response.status_code == 200:
                    content_result = ""
                    content_placeholder = st.empty()
                    
                    for chunk in content_response.iter_content(chunk_size=1024):
                        if chunk:
                            content_result += chunk.decode('utf-8')
                            content_placeholder.text(content_result[:200] + "...")
                    
                    # Lưu nội dung vào file
                    output_dir = os.path.join(st.session_state.repo_path, "wiki_output")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    file_name = f"{page['id']}.md"
                    with open(os.path.join(output_dir, file_name), "w", encoding="utf-8") as f:
                        f.write(content_result)
                    
                    # Thêm nội dung vào page object để có thể hiển thị
                    page['content'] = content_result
                    
                    st.success(f"Generated content for {page['title']} and saved to wiki_output/{file_name}")
                else:
                    st.error(f"Failed to generate content for {page['title']}: {content_response.text}")
            
            st.success(f"All content generated and saved to {os.path.join(st.session_state.repo_path, 'wiki_output')}")
            
            # Hiển thị nội dung wiki đã tạo
            st.header("🔍 Wiki Content Preview")
            
            # Tạo tabs cho từng trang
            wiki_tabs = st.tabs([page['title'] for page in st.session_state.wiki_pages])
            
            # Import streamlit_mermaid để hiển thị biểu đồ Mermaid
            from streamlit_mermaid import st_mermaid
            import re
            
            # Hiển thị từng trang trong tab tương ứng
            for i, tab in enumerate(wiki_tabs):
                with tab:
                    if 'content' in st.session_state.wiki_pages[i]:
                        content = st.session_state.wiki_pages[i]['content']
                        
                        # Tách và xử lý các đoạn mã Mermaid
                        mermaid_pattern = r'```mermaid\n(.*?)\n```'
                        mermaid_blocks = re.findall(mermaid_pattern, content, re.DOTALL)
                        
                        # Tách nội dung thành các đoạn, với đoạn Mermaid được đánh dấu đặc biệt
                        segments = re.split(mermaid_pattern, content, flags=re.DOTALL)
                        
                        # Hiển thị từng đoạn nội dung
                        for j, segment in enumerate(segments):
                            # Hiển thị phần Markdown thông thường
                            st.markdown(segment)
                            
                            # Sau mỗi đoạn Markdown, hiển thị một đoạn Mermaid nếu có
                            if j < len(mermaid_blocks):
                                with st.container():
                                    try:
                                        # Hiển thị biểu đồ Mermaid
                                        st_mermaid(mermaid_blocks[j], height=None)
                                    except Exception as e:
                                        st.error(f"Không thể hiển thị biểu đồ Mermaid: {str(e)}")
                                        st.code(mermaid_blocks[j], language="mermaid")
                    else:
                        st.info(f"Nội dung cho '{st.session_state.wiki_pages[i]['title']}' chưa được tạo hoặc không thành công.")

# Hiển thị thông tin về công cụ
st.markdown("---")
st.write("### About DeepWiki Generator")
st.write("""
This tool helps you generate comprehensive wiki documentation for your codebase using AI models. 
It performs three main functions:
1. **Analyze Code Structure** - Scans your repository to understand its organization
2. **Generate Documentation** - Creates detailed wiki pages based on your code
3. **Generate Diagrams** - Creates Mermaid diagrams to visualize architecture and flows
""")
