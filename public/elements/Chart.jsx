export default function Chart() {
  const { html } = props;
  
  console.log('=== CHART COMPONENT ===');
  console.log('Props received:', Object.keys(props));
  console.log('HTML exists:', !!html);
  console.log('HTML length:', html ? html.length : 0);
  console.log('HTML preview:', html ? html.substring(0, 100) : 'NO HTML');
  
  if (!html || html.length === 0) {
    return (
      <div style={{ 
        padding: '20px', 
        color: 'red', 
        fontWeight: 'bold',
        border: '2px solid red',
        margin: '10px'
      }}>
        ❌ No chart HTML provided (html is {typeof html})
      </div>
    );
  }
  
  return (
    <div style={{ 
      width: '100%', 
      padding: '10px',
      backgroundColor: '#f5f5f5',
      borderRadius: '8px'
    }}>
      <iframe
        srcDoc={html}
        style={{
          width: '100%',
          height: '600px',
          border: 'none',
          borderRadius: '4px',
          backgroundColor: 'white'
        }}
        title="Plotly Chart"
        sandbox="allow-scripts allow-same-origin allow-downloads"
      />
    </div>
  );
}
