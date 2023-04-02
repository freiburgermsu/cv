const headerTemplate = document.createElement('template');

headerTemplate.innerHTML = `
  <link rel="stylesheet" type="text/css" href="header.css">
  <header>
    <nav>
      <ul>
        <li><a href="CV.html">About</a></li>
        <li><a href="Reviews.html">Work</a></li>
      </ul>
    </nav>
  </header>
`;

class Header extends HTMLElement {
  constructor() {
    super();
  }

  connectedCallback() {
    
  }
}

customElements.define('header-component', Header);