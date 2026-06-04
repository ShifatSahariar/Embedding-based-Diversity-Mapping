package basic;

/* 
$Id: LList.java 1.2 1996/09/22 21:21:39 ddyer Exp ddyer $
$Log: LList.java $
Revision 1.2  1996/09/22 21:21:39  ddyer
web release 9/15/96

Revision 1.1  1996/09/18 01:18:45  ddyer
added Queue

Revision 1.2  1996/09/11 03:46:02  ddyer
added preloader

Revision 1.1  1996/09/10 02:03:30  ddyer
added list

*/

import basic.BaseObject;

import  java.util.Enumeration;

/** implements a simple list (as in "lisp") and some useful methods on it 
*/
public class LList extends BaseObject implements java.util.Enumeration{

	private Object contents;
	private LList next;

/** a list acts as it's own Enumeration */
	public Enumeration elements () { return(this); }

/** for the Enumeration protocol */
	public Object nextElement () {	return(this.next);	}

/** for the Enumeration protocol */
	public boolean hasMoreElements () {	return(this.next==null);	}

/** get the contents of this element of the list */
	public Object Contents () {	return(this.contents);	}

/** get the next element of the list */
	public LList Next () {	return(this.next); }

/** set the contents of the list to an arbitrary object */
	public void Set_Contents (Object to) {this.contents = to;	}

/** set the next element of the list (to some other list) */
	public void Set_Next (LList next) {this.next = next;	}

/* constructors */
	public LList () {	}

	public LList (Object contents, LList next) {
		this.contents = contents;
		this.next  = next;
	}

/** delete the list containing "item" from the list.  Returns a new head
for the list, so correct usage is  theList = theList.Delete_Item(object);
*/
	LList Delete_Item (Object item) {
		 LList prev=null;
		  LList cur = this;
		  while(cur!=null) {
		    if(cur.contents == item) { 
		      if(prev!=null) 
			{ prev.next = cur.next;
			  cur.next=null;
		          return(this);
		        }
		      else
		       {prev = cur.next;
		        cur.next = null;
		        return(prev);
		       }
		     }
		    prev = cur;
		    cur=cur.next;
		  }
		  return(this);
	}

/** sort the list, using "fn" to compare pairs of elements.  
 This is implemented by a bubble sort, so is only appropriate
 for short lists, hence the name.  Returns a new head for the
 list, so correct usage is theList=theList.Sort_Short_List(comparefn);
 */
	LList Sort_Short_LList (CompareFunction fn) {
		   LList out_list = this;
			 LList l=this;
		 	 LList in_list = l.next;
			l.next = null;
			while(in_list!=null) 
			{ /* scan through the in list, performing an insertion
				sort into the out list */
			LList current_list = in_list;
			Object current_item = current_list.contents;
			LList scan_list = out_list;
			LList prev_scan_list = null;
			in_list = in_list.next;
			while(scan_list!=null 
			  && !fn.InOrder(current_item,scan_list.contents)) 
				{
				prev_scan_list = scan_list;
				scan_list = scan_list.next;
				}
			current_list.next = scan_list;
			if(prev_scan_list!=null) 
			   { prev_scan_list.next = current_list; 
			   }
			   else
			   {out_list = current_list;
			   }
		    }
		  return(out_list);
	}

	// sort_short_list 
}

/* class List  */